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
from util import parse_report_details, extract_report_id
import uuid


# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
# token_path = 'tokens.json'
# if not os.path.isfile(token_path):
#     raise Exception(f"{token_path} not found!")
# with open(token_path) as f:
#     # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
#     tokens = json.load(f)
#     discord_token = tokens['discord']

discord_token = os.getenv('discord')
if not discord_token:
    raise Exception("Discord token not found in environment variables!")


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.active_replies = {} # Threads currently in moderation

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
            Message: {full_report['message']}\n\
            Abuse Type: {full_report['abuse_type']}\n\
            Additional Info: {full_report['additional_info']}\n\
            Reporting User: {author_id}\n\
            REPORT ID: {report_id}"
            self.reports.pop(author_id)
            await our_mod_channel.send(report_summary)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if isinstance(message.channel, discord.Thread) and message.channel.parent.name == f'group-{self.group_num}-mod':
            print(message.content)
            await self.handle_reply_message(message)
        else:
            return
        # # Forward the message to the mod channel
        # mod_channel = self.mod_channels[message.guild.id]
        # print(f'Guild ID is {message.guild.id}')
        # print(f'Mod channel is {mod_channel}')
        # await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        # scores = self.eval_text(message.content)
        # await mod_channel.send(self.code_format(scores))

    async def handle_reply_message(self, message):
        print(message.content)
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
        reference_report_id = extract_report_id(reference_report.content)
        reported_user, original_message, abuse_type, reporting_user = parse_report_details(reference_report.content)
        print(f"starter_message: {starter_message.content}")
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
        return message

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"


client = ModBot()
client.run(discord_token)