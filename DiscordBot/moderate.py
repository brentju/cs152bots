from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_DECISION = auto()
    DECISION_MADE = auto()
    AWAITING_REASON = auto()
    AWAITING_ACTION = auto()
    REPORT_COMPLETE = auto()
    
class ActionType(Enum):
    # enums for tracking which flow to take, given type of abuse
    TAKEDOWN = auto()
    SHADOW_BAN = auto()
    TIMEOUT = auto()
    SUSPENSION = auto()
    BAN = auto()
    ALERT_AUTHORITIES = auto()
    NONE = auto()

class Moderate:
    START_KEYWORD = "START"
    CANCEL_KEYWORD = "CANCEL"
    END_KEYWORD = "END"
    HELP_KEYWORD = "HELP"

    def __init__(self, client, reporting_user, reported_user, initial_message, abuse_type):
        self.state = State.REPORT_START
        self.client = client
        self.decision = None
        self.reason = None
        self.action = None
        self.perp_message = inital_message
        self.reporting_user = reporting_user
        self.reported_user = reported_user
        self.abuse_type = abuse_type
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Starting the moderation process. "
            reply += "Please provide whether or not you believe this message should be removed."
            self.state = State.AWAITING_DECISION
            return [reply]
        
        if self.state == State.AWAITING_DECISION:
            # Parse out the three ID strings from the message link
            m = message.content.strip().lower()
            if m == "yes":
                return
            else:
                self.state = State.DECISION_MADE
        if self.state == State.DECISION_MADE:
            pass
        if self.state == State.AWAITING_REASON:
            pass
        if self.state == State.AWAITING_ACTION:
            pass

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
    
    async def notify_users(self):
        # Send notifications to reported and reporting users
        reported_message = f"Your message: '{self.initial_message.content}' was moderated. Action: {self.action}, Reason: {self.reason}."
        reporting_message = f"Your report regarding the message: '{self.initial_message.content}' was addressed. Action: {self.action}, Reason: {self.reason}. Thank you for reporting!"
        await self.reported_user.send(reported_message)
        await self.reporting_user.send(reporting_message)

