from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_ABUSE_TYPE = auto()   
     
    # enums to track unified flow once specific abuse details provided
    AWAITING_ADDL_INFO = auto()
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

    def __init__(self, client):
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
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
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
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Would you like to report the following as:", \
                    "1. NSFW", "2. Impersonation", "3. Hateful Content", "4. Copyright Infringement", "5. Other"]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            # We are awaiting a reply to the above
            abuse_type = None
            msg_key = None
            try:
                msg_key = int(message.content)
                if int(message.content) in self.abuse_types.keys(): 
                    abuse_type = self.abuse_types[int(message.content)]
            except ValueError:
                pass
            if message.content.lower() in self.abuse_types.values():
                abuse_type = message.content.lower()
                
            if abuse_type:
                # self.state = State.AWAITING_ADDL_INFO
                self.cur_abuse_type = abuse_type
                return [f"I see you have identified the message as {abuse_type}. Please provide some additional information/context to help us address your report."]
            return ["Sorry, I didn't quite understand. Please try again or say `cancel` to cancel.", \
                "1. NSFW", "2. Impersonation", "3. Hateful Content", "4. Copyright Infringement", "5. Other"]
            
        if self.state == State.AWAITING_ADDL_INFO:
            return ["TBD: But at least you got to this point!"]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

