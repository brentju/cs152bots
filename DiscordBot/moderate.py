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
        self.perp_message = initial_message
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
            reply += "Please provide whether or not you believe this message should be removed (y/n)"
            self.state = State.AWAITING_DECISION
            return [reply]
        
        if self.state == State.AWAITING_DECISION:
            # Parse out the three ID strings from the message link
            m = message.content.strip().lower()
            if m == "n" or m == "no":
                self.decision = "not remove"
            else:
                self.decision = "remove"
            self.state = State.AWAITING_REASON
            reply = f"You have chosen to {self.decision} this post."
            reply += "Please provide a reason for why, as well as a reference to our TOS."
            return [reply]
        if self.state == State.AWAITING_REASON:
            self.reason = message.content
            reply = "Thank you."
            if self.decision == "not_remove":
                self.state = State.REPORT_COMPLETE
                reply += "Your report is complete."
            else:
                reply+= "Please provide the action you wish to take regarding the post and/or it's owner."
                self.state = State.AWAITING_ACTION
                reply += """ Your choices are as follows:
                1. Remove the post\n2. Shadow ban the user\n3. Prevent the user from posting for 24h\n4. Suspend the user for a week\n\
                5. Ban the account\n6. Ban the user\n7. Report the user to authorities"""
                reply += "Please respond with the corresponding number."
            return [reply]
        if self.state == State.AWAITING_ACTION:
            m = int(message.content.strip().lower())
            self.state = State.REPORT_COMPLETE
            reply = "Report complete."
            if m == 1:
                self.action = "Remove post"
            elif m == 2:
                self.action = "Shadow ban"
            elif m == 3:
                self.action = "24hr timeout"
            elif m == 4:
                self.action = "Suspension for a week"
            elif m == 5:
                self.action = "Ban account"
            elif m == 6:
                self.action = "Ban user"
            elif m == 7:
                self.action = "Report to authorities"
            else:
                reply = "Could not parse your response. Please try again."
                self.state = State.AWAITING_ACTION
            return [reply]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    
    async def notify_users(self):
        # Send notifications to reported and reporting users
        reported_message = f"Your message: '{self.initial_message.content}' was moderated. Action: {self.action}, Reason: {self.reason}."
        reporting_message = f"Your report regarding the message: '{self.initial_message.content}' was addressed. Action: {self.action}, Reason: {self.reason}. Thank you for reporting!"
        await self.reported_user.send(reported_message)
        await self.reporting_user.send(reporting_message)

