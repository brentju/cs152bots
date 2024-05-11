from enum import Enum, auto
import discord
import re
from util import extract_report_id, remove_report_id

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_ABUSE_TYPE = auto()   
     
    # enums to track unified flow once specific abuse details provided
    AWAITING_ABUSE_SUBTYPE = auto()
    AWAITING_ADDL_INFO = auto()
    AWAITING_USER_BLOCK = auto()
    REPORT_COMPLETE = auto()
    
class AbuseType(Enum):
    # enums for tracking which flow to take, given type of abuse
    NSFW = auto()
    IMPERSONATION = auto()
    HATEFUL = auto()
    COPYRIGHT = auto()
    OTHER = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client, report_id):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.abuse_types = {
            1: "nsfw",
            2: "impersonation",
            3: "hateful content",
            4: "copyright infringement",
            5: "other"
        }
        self.cur_abuse_type = None
        self.reported_user = None
        self.reported_by = None
        self.user_addl_info = None
        self.guild_id = None
        self.report_id = report_id
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''
        report_id = extract_report_id(message.content)
        print(message.content)
        if report_id:
            message.content = remove_report_id(message.content)
            (print(message.content))
        else:
            if self.state != State.REPORT_START:
                return ["Please remember to include the report ID in your report!"]
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += f"For all further steps of the reporting process, please preface your message with the following message: \n REPORT ID: {self.report_id}\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            self.guild_id = guild
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            self.reported_user = message.author
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Would you like to report the following as:", \
                    "1. NSFW", "2. Impersonation", "3. Hateful Content", "4. Copyright Infringement", "5. Other"]
            self.message = message.content
        if self.state == State.MESSAGE_IDENTIFIED:
            # We are awaiting a reply to the above
            abuse_type = None
            msg_key = None
            # attempt to parse out the type of abuse user specifies
            try:
                msg_key = int(message.content)
                if int(message.content) in self.abuse_types.keys(): 
                    abuse_type = self.abuse_types[int(message.content)]
            except ValueError:
                pass
            if message.content.lower() in self.abuse_types.values():
                abuse_type = message.content.lower()
                
            if abuse_type:
                self.cur_abuse_type = abuse_type
                self.state = State.AWAITING_ABUSE_SUBTYPE
                reply = f"I see you have identified the message as {abuse_type}.\n"
                if self.cur_abuse_type != "other":
                    reply += "Can you please provide some more specifics on what category of abuse this falls under?\n"
                reply += self.add_context(abuse_type)
                return [reply]
            return ["Sorry, I didn't quite understand. Please try again or say `cancel` to cancel.", \
                "1. NSFW", "2. Impersonation", "3. Hateful Content", "4. Copyright Infringement", "5. Other"]

        if self.state == State.AWAITING_ABUSE_SUBTYPE:
            # leveraging a helper function to parse out
            subtypes = [subtype.lower() for subtype in self.add_context(self.cur_abuse_type).split("\n")]
            for subtype in subtypes:
                if message.content.lower() in subtype:
                    # use string slicing to cut out list index included inside string.
                    subtype = subtype[3:]
                    reply = f"You have identified your abuse subtype as {subtype}.\n"
                    reply += "Please provide some additional context so we can better handle your report.\n"
                    self.state = State.AWAITING_ADDL_INFO
                    return [reply]
            response = "I didn't quite get that; please try again or cancel.\n"
            response += subtypes
            return response

        if self.state == State.AWAITING_ADDL_INFO:
            self.state = State.AWAITING_USER_BLOCK
            self.user_addl_info = message.content
            return ["Thank you for your report! Would you like to block this user? (y/n)"]

        if self.state == State.AWAITING_USER_BLOCK:
            msg = message.content.lower()
            if msg == "y" or msg == "yes":
                self.state = State.REPORT_COMPLETE
                return [f"We have blocked user {self.reported_user.name}. Thank you for your report; we will review your report and take action accordingly. We appreciate your effort in helping make TikTok a safer place for everyone."]
            elif msg == "n" or msg == "no":
                self.state = State.REPORT_COMPLETE
                return [f"Thank you for your report; we will review your report and take action accordingly. We appreciate your effort in helping make TikTok a safer place for everyone."]
            response = "I didn't quite get that; please either enter a y/n character, \"yes,\" or \"no.\""
            return [response]

        return ["no state detected."]

    """
    Provide additional context options to the message for the user,
    dependent on the abuse type specified.

    @params:
    abuse_type (str): Specified abuse type, guaranteed to be one of the below 5 types.

    @returns:
    A string containing the subcategories of each abuse type.
    """
    def add_context(self, abuse_type):
        if abuse_type == "nsfw":
            return "1. Nudity\n2. Violence\n3. CSAM"
        elif abuse_type == "impersonation":
            return "1. Propaganda/Libel\n2. Imitating Public Figures\n3. Imitating others\n4. Fraud/Scam/Catfishing\n5. Impersonating myself"
        elif abuse_type == "hateful content":
            return "1. Hateful content\n2. Targeted Harassment\n3. Inciting violence"
        elif abuse_type == "copyright infringement":
            return "1. Audio\n2. Video\n3. Photo"
        elif abuse_type == "other":
            self.state = State.AWAITING_ADDL_INFO
            return "Please provide some additional context so we can better handle your report.\n"


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    
    def get_full_report(self):
        return {
            "message": self.message,
            "abuse_type": self.cur_abuse_type,
            "reported_user": self.reported_user,
            "additional_info": self.user_addl_info,
        }

    

