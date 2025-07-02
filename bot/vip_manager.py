"""
VIP User Management Module
Handles VIP user operations, DM tracking, and channel-specific conversation filtering
"""
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from django.utils import timezone
from django.conf import settings
import google.generativeai as genai

from .models import VIPUser, VIPSummaryHistory
from .summarizer import ChannelSummarizer

logger = logging.getLogger(__name__)


class VIPManager:
    """
    Handles all VIP user management operations and specialized summarization
    """
    
    def __init__(self, slack_client: WebClient):
        """Initialize VIP manager with Slack client"""
        self.client = slack_client
        self.summarizer = ChannelSummarizer()
        
        # Configure Gemini for VIP-specific summarization
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.generation_config = genai.types.GenerationConfig(
                temperature=0.3,
                top_p=0.8,
                top_k=40,
                max_output_tokens=2048,
            )
    
    # VIP User Management Methods
    
    def add_vip_user(self, user_id: str, added_by: str) -> Tuple[bool, str]:
        """
        Add a user to the VIP list for a specific user
        
        Args:
            user_id: Slack user ID to add as VIP
            added_by: User ID of who is adding the VIP (VIP list owner)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if user is trying to add themselves
            if user_id == added_by:
                return False, f"❌ You cannot add yourself as a VIP"
            
            # Get user info from Slack
            user_info = self._get_user_info(user_id)
            if not user_info:
                return False, f"❌ User <@{user_id}> not found in workspace"
            
            # Check if already VIP for this user
            if VIPUser.objects.filter(user_id=user_id, added_by=added_by, is_active=True).exists():
                return False, f"❌ <@{user_id}> is already in your VIP list"
            
            # Create or reactivate VIP user
            vip_user, created = VIPUser.objects.get_or_create(
                user_id=user_id,
                added_by=added_by,
                defaults={
                    'username': user_info.get('name', f'user_{user_id}'),
                    'display_name': user_info.get('real_name', user_info.get('name', 'Unknown')),
                    'is_active': True
                }
            )
            
            if not created:
                # Reactivate existing VIP
                vip_user.is_active = True
                vip_user.added_at = timezone.now()
                vip_user.save()
            
            logger.info(f"VIP user added: {user_id} by {added_by}")
            return True, f"✅ <@{user_id}> has been added to your VIP list"
            
        except Exception as e:
            logger.error(f"Error adding VIP user {user_id}: {str(e)}")
            return False, f"❌ Error adding VIP user: {str(e)}"
    
    def remove_vip_user(self, user_id: str, removed_by: str) -> Tuple[bool, str]:
        """
        Remove a user from the VIP list for a specific user
        
        Args:
            user_id: Slack user ID to remove from VIP list
            removed_by: User ID of who is removing the VIP (VIP list owner)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            vip_user = VIPUser.objects.filter(user_id=user_id, added_by=removed_by, is_active=True).first()
            if not vip_user:
                return False, f"❌ <@{user_id}> is not in your VIP list"
            
            vip_user.is_active = False
            vip_user.save()
            
            logger.info(f"VIP user removed: {user_id} by {removed_by}")
            return True, f"✅ <@{user_id}> has been removed from your VIP list"
            
        except Exception as e:
            logger.error(f"Error removing VIP user {user_id}: {str(e)}")
            return False, f"❌ Error removing VIP user: {str(e)}"
    
    def is_vip_user(self, user_id: str, vip_list_owner: str) -> bool:
        """
        Check if a user is in the VIP list for a specific user
        
        Args:
            user_id: Slack user ID to check
            vip_list_owner: User ID of the VIP list owner
            
        Returns:
            True if user is VIP for the list owner, False otherwise
        """
        return VIPUser.objects.filter(user_id=user_id, added_by=vip_list_owner, is_active=True).exists()
    
    def get_all_vips(self, vip_list_owner: str) -> List[VIPUser]:
        """
        Get all active VIP users for a specific user
        
        Args:
            vip_list_owner: User ID of the VIP list owner
            
        Returns:
            List of active VIP users for the specified owner
        """
        return VIPUser.objects.filter(added_by=vip_list_owner, is_active=True).order_by('-added_at')
    
    def get_vip_by_username(self, username: str, vip_list_owner: str) -> Optional[VIPUser]:
        """
        Get VIP user by username (with or without @) for a specific user
        
        Args:
            username: Username to search for
            vip_list_owner: User ID of the VIP list owner
            
        Returns:
            VIPUser object if found, None otherwise
        """
        # Remove @ if present
        clean_username = username.lstrip('@')
        
        return VIPUser.objects.filter(
            username=clean_username,
            added_by=vip_list_owner,
            is_active=True
        ).first()
    
    # VIP DM Summarization Methods
    
    def get_vip_dm_messages(self, vip_user_id: str, since_timestamp: Optional[float] = None) -> List[Dict]:
        """
        Retrieve DM conversation history with VIP user
        
        Args:
            vip_user_id: VIP user's Slack ID
            since_timestamp: Timestamp to get messages since (default: last 24 hours)
            
        Returns:
            List of DM messages
        """
        try:
            if since_timestamp is None:
                # Default to last 24 hours
                since_timestamp = (datetime.now() - timedelta(hours=24)).timestamp()
            
            logger.info(f"Retrieving DM messages for VIP user {vip_user_id} since {datetime.fromtimestamp(since_timestamp)}")
            
            # Get DM channel with VIP user
            dm_channel = self._get_dm_channel(vip_user_id)
            if not dm_channel:
                logger.warning(f"No DM channel found for VIP user {vip_user_id}")
                return []
            
            logger.info(f"Found DM channel {dm_channel} for VIP user {vip_user_id}")
            
            # Fetch messages from DM channel
            messages = []
            cursor = None
            
            while True:
                response = self.client.conversations_history(
                    channel=dm_channel,
                    oldest=str(since_timestamp),
                    limit=200,
                    cursor=cursor
                )
                
                batch_messages = response.get('messages', [])
                messages.extend(batch_messages)
                logger.info(f"Retrieved {len(batch_messages)} messages in this batch (total so far: {len(messages)})")
                
                if not response.get('has_more'):
                    break
                
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
            
            logger.info(f"Retrieved {len(messages)} total raw messages for VIP {vip_user_id}")
            
            # Filter out bot messages and sort chronologically
            filtered_messages = [
                msg for msg in messages 
                if not msg.get('subtype') and msg.get('text') and msg.get('text').strip()
            ]
            
            logger.info(f"After filtering, {len(filtered_messages)} messages remain for VIP {vip_user_id}")
            
            # Log a sample of messages for debugging
            if filtered_messages:
                logger.info(f"Sample message: {filtered_messages[0]}")
            
            return sorted(filtered_messages, key=lambda x: float(x.get('ts', 0)))
            
        except SlackApiError as e:
            logger.error(f"SlackApiError fetching VIP DM messages for {vip_user_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching VIP DM messages for {vip_user_id}: {e}")
            return []
    
    def summarize_vip_dms(self, vip_user: VIPUser, messages: List[Dict], requested_by: str) -> str:
        """
        Generate AI summary of VIP DM conversations
        
        Args:
            vip_user: VIP user object
            messages: List of DM messages
            requested_by: User ID who requested the summary
            
        Returns:
            AI-generated summary of DM conversations
        """
        if not messages:
            return self._generate_empty_dm_summary(vip_user.username)
        
        formatted_messages = self._format_dm_messages_for_analysis(messages, vip_user.user_id)
        
        prompt = f"""
        Please analyze these Direct Message conversations with VIP user @{vip_user.username} and provide a summary in EXACTLY this format:

        VIP DM Summary for @{vip_user.username}

        Time Period Covered
        • {self._get_time_period_text(messages)}

        Key Discussion Topics
        • [First major topic discussed with period.]
        • [Second major topic discussed with period.]
        • [Third major topic discussed with period.]

        Important Decisions & Requests
        • [First decision or request with period.]
        • [Second decision or request with period.]

        Action Items & Follow-ups
        • [First action item with period.]
        • [Second action item with period.]

        VIP Insights
        • Personal Updates: [Key personal/professional updates shared.]
        • Concerns Raised: [Any concerns or issues mentioned.]
        • Expertise Shared: [Specialized knowledge or advice given.]

        Summary Details
        Messages analyzed: {len(messages)}
        VIP: {vip_user.display_name} (@{vip_user.username})
        Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

        CRITICAL FORMATTING RULES:
        1. Use ONLY the bullet character "•" (not emojis, dashes, or asterisks)
        2. Add exactly one line break after each bullet point
        3. End each bullet point with proper punctuation
        4. Keep section titles EXACTLY as shown
        5. Use exactly two line breaks between sections
        6. Focus on VIP's personal communications and private discussions
        7. Highlight decisions made in private conversations
        8. Identify action items and commitments from DMs

        DM CONVERSATIONS TO ANALYZE:
        {formatted_messages}
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            summary = response.text.strip() if response.text else self._generate_error_dm_summary(vip_user.username, "No AI response")
            
            # Save summary to history
            VIPSummaryHistory.objects.create(
                vip_user=vip_user,
                summary_type='dm',
                last_summarized_at=timezone.now(),
                summary_content=summary,
                requested_by=requested_by,
                messages_count=len(messages),
                timeframe_hours=24
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating VIP DM summary for {vip_user.username}: {str(e)}")
            return self._generate_error_dm_summary(vip_user.username, str(e))
    
    # VIP Channel Activity Methods
    
    def get_vip_channel_messages(self, vip_user_id: str, channel_id: str, since_timestamp: Optional[float] = None) -> List[Dict]:
        """
        Filter channel messages to show only VIP's contributions and related context
        
        Args:
            vip_user_id: VIP user's Slack ID
            channel_id: Channel ID to analyze
            since_timestamp: Timestamp to get messages since (default: last 24 hours)
            
        Returns:
            List of VIP-related channel messages with context
        """
        try:
            if since_timestamp is None:
                since_timestamp = (datetime.now() - timedelta(hours=24)).timestamp()
            
            # Get all channel messages
            all_messages = self._get_channel_messages(channel_id, since_timestamp)
            
            # Filter for VIP-related messages
            vip_messages = []
            
            for i, message in enumerate(all_messages):
                # Include VIP's own messages
                if message.get('user') == vip_user_id:
                    vip_messages.append(message)
                
                # Include messages mentioning the VIP
                elif self._message_mentions_user(message, vip_user_id):
                    vip_messages.append(message)
                
                # Include replies to VIP's messages
                elif self._is_reply_to_vip(message, vip_user_id, all_messages[:i]):
                    vip_messages.append(message)
            
            return vip_messages
            
        except Exception as e:
            logger.error(f"Error getting VIP channel messages for {vip_user_id} in {channel_id}: {str(e)}")
            return []
    
    def summarize_vip_channel_activity(self, vip_user: VIPUser, channel_id: str, channel_name: str, messages: List[Dict], requested_by: str) -> str:
        """
        Generate AI summary of VIP's channel activity and contributions
        
        Args:
            vip_user: VIP user object
            channel_id: Channel ID
            channel_name: Channel name for display
            messages: List of VIP-related channel messages
            requested_by: User ID who requested the summary
            
        Returns:
            AI-generated summary of VIP's channel activity
        """
        if not messages:
            return self._generate_empty_channel_summary(vip_user.username, channel_name)
        
        formatted_messages = self._format_channel_messages_for_analysis(messages, vip_user.user_id)
        
        prompt = f"""
        Please analyze VIP user @{vip_user.username}'s activity in #{channel_name} and provide a summary in EXACTLY this format:

        VIP Channel Summary for @{vip_user.username} in #{channel_name}

        Time Period Covered
        • {self._get_time_period_text(messages)}

        VIP's Key Contributions
        • [First major contribution or insight with period.]
        • [Second major contribution or insight with period.]
        • [Third major contribution or insight with period.]

        Context Within Broader Discussions
        • [How VIP's input influenced team discussions with period.]
        • [Key interactions with other team members with period.]

        Leadership & Decision Impact
        • [Decisions influenced by VIP with period.]
        • [Guidance or direction provided by VIP with period.]

        Mentions & Interactions
        • Times Mentioned: [How often VIP was mentioned or tagged.]
        • Replies Received: [Notable responses to VIP's messages.]
        • Collaborations: [Key collaborative moments with team.]

        Expertise & Value Added
        • [Specialized knowledge shared by VIP with period.]
        • [Problems solved or insights provided with period.]

        Summary Details
        Messages analyzed: {len(messages)}
        VIP: {vip_user.display_name} (@{vip_user.username})
        Channel: #{channel_name}
        Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

        CRITICAL FORMATTING RULES:
        1. Use ONLY the bullet character "•" (not emojis, dashes, or asterisks)
        2. Add exactly one line break after each bullet point
        3. End each bullet point with proper punctuation
        4. Keep section titles EXACTLY as shown
        5. Use exactly two line breaks between sections
        6. Focus specifically on the VIP's contributions and impact
        7. Highlight their influence on team discussions and decisions
        8. Show how their expertise added value to conversations

        VIP CHANNEL ACTIVITY TO ANALYZE:
        {formatted_messages}
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            summary = response.text.strip() if response.text else self._generate_error_channel_summary(vip_user.username, channel_name, "No AI response")
            
            # Save summary to history
            VIPSummaryHistory.objects.create(
                vip_user=vip_user,
                summary_type='channel',
                channel_id=channel_id,
                channel_name=channel_name,
                last_summarized_at=timezone.now(),
                summary_content=summary,
                requested_by=requested_by,
                messages_count=len(messages),
                timeframe_hours=24
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating VIP channel summary for {vip_user.username} in {channel_name}: {str(e)}")
            return self._generate_error_channel_summary(vip_user.username, channel_name, str(e))
    
    # Helper Methods
    
    def _get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get user information from Slack API"""
        try:
            response = self.client.users_info(user=user_id)
            return response.get('user', {}) if response.get('ok') else None
        except SlackApiError as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return None
    
    def _get_dm_channel(self, user_id: str) -> Optional[str]:
        """Get DM channel ID for user"""
        try:
            logger.info(f"Opening DM channel with user {user_id}")
            response = self.client.conversations_open(users=[user_id])
            
            if response.get('ok'):
                channel_id = response.get('channel', {}).get('id')
                logger.info(f"Successfully opened DM channel {channel_id} with user {user_id}")
                return channel_id
            else:
                error = response.get('error', 'unknown_error')
                logger.error(f"Failed to open DM channel with {user_id}: {error}")
                return None
                
        except SlackApiError as e:
            logger.error(f"SlackApiError opening DM channel with {user_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error opening DM channel with {user_id}: {e}")
            return None
    
    def _get_channel_messages(self, channel_id: str, since_timestamp: float) -> List[Dict]:
        """Get all messages from a channel since timestamp"""
        try:
            messages = []
            cursor = None
            
            while True:
                response = self.client.conversations_history(
                    channel=channel_id,
                    oldest=str(since_timestamp),
                    limit=200,
                    cursor=cursor
                )
                
                messages.extend(response.get('messages', []))
                
                if not response.get('has_more'):
                    break
                
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
            
            return sorted(messages, key=lambda x: float(x.get('ts', 0)))
            
        except SlackApiError as e:
            logger.error(f"Error fetching channel messages for {channel_id}: {e}")
            return []
    
    def _message_mentions_user(self, message: Dict, user_id: str) -> bool:
        """Check if message mentions specific user"""
        text = message.get('text', '')
        return f'<@{user_id}>' in text
    
    def _is_reply_to_vip(self, message: Dict, vip_user_id: str, previous_messages: List[Dict]) -> bool:
        """Check if message is a reply to VIP's message"""
        # Check if message has thread_ts and if the parent message is from VIP
        thread_ts = message.get('thread_ts')
        if not thread_ts:
            return False
        
        # Find the parent message
        for prev_msg in previous_messages:
            if prev_msg.get('ts') == thread_ts and prev_msg.get('user') == vip_user_id:
                return True
        
        return False
    
    def _format_dm_messages_for_analysis(self, messages: List[Dict], vip_user_id: str) -> str:
        """Format DM messages for AI analysis"""
        formatted_messages = []
        
        for message in messages:
            timestamp = datetime.fromtimestamp(float(message.get('ts', 0)))
            user = message.get('user', 'Unknown')
            text = message.get('text', '')
            
            # Clean up Slack formatting
            text = self.summarizer._clean_slack_formatting(text)
            
            if text.strip():
                # Mark who is speaking (VIP or Bot)
                speaker = "VIP" if user == vip_user_id else "Bot"
                formatted_message = f"[{timestamp.strftime('%Y-%m-%d %H:%M')}] {speaker}: {text}"
                formatted_messages.append(formatted_message)
        
        return "\n".join(formatted_messages)
    
    def _format_channel_messages_for_analysis(self, messages: List[Dict], vip_user_id: str) -> str:
        """Format channel messages for AI analysis with VIP context"""
        formatted_messages = []
        
        for message in messages:
            timestamp = datetime.fromtimestamp(float(message.get('ts', 0)))
            user = message.get('user', 'Unknown')
            text = message.get('text', '')
            
            # Clean up Slack formatting
            text = self.summarizer._clean_slack_formatting(text)
            
            if text.strip():
                # Mark VIP messages specially
                if user == vip_user_id:
                    formatted_message = f"[{timestamp.strftime('%Y-%m-%d %H:%M')}] **VIP**: {text}"
                else:
                    formatted_message = f"[{timestamp.strftime('%Y-%m-%d %H:%M')}] {user}: {text}"
                formatted_messages.append(formatted_message)
        
        return "\n".join(formatted_messages)
    
    def _get_time_period_text(self, messages: List[Dict]) -> str:
        """Generate time period text from messages"""
        if not messages:
            return "No messages in timeframe"
        
        first_ts = float(messages[0].get('ts', 0))
        last_ts = float(messages[-1].get('ts', 0))
        
        start_time = datetime.fromtimestamp(first_ts)
        end_time = datetime.fromtimestamp(last_ts)
        
        return f"{start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}"
    
    # Error and Empty Summary Generators
    
    def _generate_empty_dm_summary(self, username: str) -> str:
        """Generate empty DM summary"""
        return f"""VIP DM Summary for @{username}

Time Period Covered
• No messages found in the last 24 hours

Key Discussion Topics
• No recent DM conversations to analyze

Important Decisions & Requests
• No decisions or requests in recent messages

Action Items & Follow-ups
• No action items identified

VIP Insights
• Personal Updates: No recent updates shared
• Concerns Raised: No concerns identified
• Expertise Shared: No expertise shared recently

Summary Details
Messages analyzed: 0
VIP: @{username}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}"""
    
    def _generate_empty_channel_summary(self, username: str, channel_name: str) -> str:
        """Generate empty channel summary"""
        return f"""VIP Channel Summary for @{username} in #{channel_name}

Time Period Covered
• No VIP activity found in the last 24 hours

VIP's Key Contributions
• No recent contributions from VIP in this channel

Context Within Broader Discussions
• VIP was not active in recent channel discussions

Leadership & Decision Impact
• No recent leadership moments identified

Mentions & Interactions
• Times Mentioned: 0
• Replies Received: 0
• Collaborations: No recent collaborations

Expertise & Value Added
• No expertise shared recently in this channel

Summary Details
Messages analyzed: 0
VIP: @{username}
Channel: #{channel_name}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}"""
    
    def _generate_error_dm_summary(self, username: str, error: str) -> str:
        """Generate error DM summary"""
        return f"""VIP DM Summary for @{username}

❌ Error generating summary: {error}

Please try again later or contact support if the issue persists.

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}"""
    
    def _generate_error_channel_summary(self, username: str, channel_name: str, error: str) -> str:
        """Generate error channel summary"""
        return f"""VIP Channel Summary for @{username} in #{channel_name}

❌ Error generating summary: {error}

Please try again later or contact support if the issue persists.

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}""" 