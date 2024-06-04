# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
import pdb
from moderate import Moderate
from util import parse_report_details, extract_report_id, download_image
import uuid
from PIL import Image
import torchvision
import torch
from torchvision import transforms
from model.model import CNNModel
from io import BytesIO
from google.cloud import vision
import boto3

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']

# discord_token = os.getenv('discord')
# if not discord_token:
#     raise Exception("Discord token not found in environment variables!")


class ModBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.active_replies = {} # Threads currently in moderation
        self.model = CNNModel()
        self.model.load_state_dict(torch.load("./model/cnn_finetuned.pth"))
        self.transforms = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        self.vision_client = vision.ImageAnnotatorClient()
        self.rekognition_client = boto3.client('rekognition')

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel


    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs).
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel.
        '''
        # Ignore messages from the bot
        if message.author.id == self.user.id:
            return

        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to us
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            our_guild_id = 1211760623969370122
            our_mod_channel = self.mod_channels[our_guild_id]
            full_report = self.reports[author_id].get_full_report()
            report_id = uuid.uuid4()
            report_summary = f"Full report for {message.author.display_name}:\n\
            Reported User: {full_report['reported_user']} \n\
            Message: {full_report['message'].content}\n\
            Abuse Type: {full_report['abuse_type']}\n\
            Additional Info: {full_report['additional_info']}\n\
            Reporting User: {author_id}\n\
            REPORT ID: {report_id}"
            if full_report['message'].attachments:
                attachments = full_report['message'].attachments
                for attachment in attachments:
                    report_summary += f"Message included attachment: {attachment.url}\n"
            self.reports.pop(author_id)
            await our_mod_channel.send(report_summary)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if isinstance(message.channel, discord.Thread) and message.channel.parent.name == f'group-{self.group_num}-mod':
            await self.handle_reply_message(message)
        elif message.channel.name == f'group-{self.group_num}':
            # Forward the message to the mod channel
            mod_channel = self.mod_channels[message.guild.id]
            image_detected, analysis = self.eval_text(message)
            if not image_detected:
                return
            else:
                await(self.message_actions(message, analysis))

    async def handle_reply_message(self, message):
        if message.content == Moderate.HELP_KEYWORD:
            reply =  "Use the `START` command to begin the moderation process.\n"
            reply += "Use the `CANCEL` command to cancel the moderation process.\n"
            reply += "Use the `END` command to end the moderation process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        if author_id not in self.active_replies and not message.content.startswith(Moderate.START_KEYWORD):
            return

        thread = message.channel
        starter_message = await thread.parent.fetch_message(thread.id)
        reference_report = starter_message
        details = parse_report_details(reference_report.content)
        reported_user = details['reported_user']
        original_message = details['message']
        abuse_type = details['abuse_type']
        reporting_user = details['reporting_user']
        reference_report_id = details['report_id']
        print(f"reported_user: {reported_user}")
        print(f"original_message: {original_message}")
        print(f"abuse_type: {abuse_type}")
        print(f"reporting_user: {reporting_user}")
        if message.author.id not in self.active_replies:
            self.active_replies[message.author.id] = {}
        if reference_report_id not in self.active_replies[message.author.id]:
            self.active_replies[message.author.id][reference_report_id] = Moderate(self,
                                                                                   reporting_user=reporting_user,
                                                                                   initial_message=original_message,
                                                                                   abuse_type=abuse_type,
                                                                                   reported_user=reported_user)
        print(f"Author: {message.author}")
        print(f"Active replies for this author are: {self.active_replies[message.author.id]}")
        responses = await self.active_replies[message.author.id][reference_report_id].handle_message(message)
        print(responses)
        for r in responses:
            await message.channel.send(r)

        if self.active_replies[author_id][reference_report_id].report_complete():
            moderation = self.active_replies[author_id][reference_report_id]
            await moderation.notify_users()
            del self.active_replies[message.author.id][reference_report_id]


    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel,
        insert your code here! This will primarily be used in Milestone 3.
        '''
        if message.attachments:
            print("attachment detected")
            for attachment in message.attachments:
                print(attachment.url)
                response = requests.get(attachment.url)
                if response.status_code == 200:
                    image = Image.open(BytesIO(response.content))
                    image = image.convert("RGB")
                    image_tensor = self.transforms(image)
                    image_tensor = image_tensor.unsqueeze(0)

                    # Check if artificially generated
                    output = self.model(image_tensor)
                    softmax = torch.nn.Softmax()
                    output = softmax(output[0])
                    print(type(output[0]))

                    # Safesearch results
                    image_bytes = BytesIO(response.content).getvalue()
                    safe_search_results = self.check_safe_search(image_bytes)

                    # Rekognition results
                    celebrities = self.check_celebs(image_bytes)

                    print(celebrities)
                    print(safe_search_results)

                    analysis = {
                        'artificially_generated_confidence': output.detach().numpy()[0],
                        'violence': safe_search_results['violence'].name,
                        'adult': safe_search_results['adult'].name,
                        'spoof': safe_search_results['spoof'].name,
                        'racy': safe_search_results['racy'].name,
                        'celebrity_ids': [
                            {
                                'name': celeb['Name'],
                                'confidence': celeb['MatchConfidence']
                            } for celeb in celebrities
                        ]
                    }
                    return True, analysis
        return False, {}

    def check_safe_search(self, image_bytes):
        image = vision.Image(content=image_bytes)
        response = self.vision_client.safe_search_detection(image=image)
        safe_search = response.safe_search_annotation
        return {
            'violence': safe_search.violence,
            'adult': safe_search.adult,
            'spoof': safe_search.spoof,
            'racy': safe_search.racy
        }

    def check_celebs(self, image_bytes):
        response = self.rekognition_client.recognize_celebrities(
            Image={'Bytes': image_bytes}
        )
        return response['CelebrityFaces']

    async def message_actions(self, message, analysis):
        ai_generated_threshold = 0.85
        celebrity_confidence_threshold = 0.9
        if analysis['artificially_generated_confidence'] > ai_generated_threshold:
            if (analysis['violence'] == 'VERY_LIKELY' or analysis['adult'] == 'VERY_LIKELY' or
                    analysis['racy'] == 'VERY_LIKELY'):
                await self.send_to_moderators(message, analysis, "Potentially unsafe content detected.")
                await message.delete()
                await message.channel.send(f"Removed a potentially unsafe AI-generated media from {message.author.mention}.")
            elif analysis['spoof'] == "VERY_LIKELY":
                if analysis['celebrity_ids']:
                    for celebrity in analysis['celebrity_ids']:
                        if celebrity['confidence'] > celebrity_confidence_threshold:
                            await self.send_to_moderators(message, analysis, "AI-generated spoof of a celebrity")
                            await message.delete()
                            await message.channel.send(f"Removed an AI-generated spoof of a celebrity from {message.author.mention}")
                            break
            else:
                await message.channel.send(self.code_format(analysis['artificially_generated_confidence']))
        elif (analysis['violence'] == 'VERY_LIKELY' or analysis['adult'] == 'VERY_LIKELY' or analysis['racy'] == 'VERY_LIKELY'):
            await self.send_to_moderators(message, analysis, "Potentially unsafe real content")

    async def send_to_moderators(self, message, analysis, description):
        our_guild_id = 1211760623969370122
        our_mod_channel = self.mod_channels[our_guild_id]

        report_summary = f"Full report for {message.author.display_name}:\n"
        report_summary += f"\tReported User: {message.author.id} \n"
        report_summary += f"\tMessage: {message.content}\n"
        report_summary += f"\tAbuse Type: {description}\n"
        report_summary += f"\tAdditional Info: {analysis}\n"

        report_summary += f"\tReporting User: automatic\n"
        report_summary += f"\tREPORT ID: {uuid.uuid4()}"

        if message.content:
            attachments = message.attachments
            for attachment in attachments:
                report_summary += f"\tMessage included attachment: {attachment.url}\n"

        await our_mod_channel.send(report_summary)

    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been
        evaluated, insert your code here for formatting the string to be
        shown in the mod channel.
        '''
        score = f"{text * 100:.2f}%"
        return f"GenAIBot: Careful, based on my analysis, this has a high chance of being AI generated."


client = ModBot()
client.run(discord_token)
