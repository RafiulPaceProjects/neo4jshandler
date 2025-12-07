import logging
from typing import Optional
from graphbot.services.llm import LLMProvider

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Manages context window usage, including truncation and token counting.
    """
    
    def __init__(self, provider: LLMProvider, max_tokens: int = 30000, strategy: str = "last_k_messages"):
        self.provider = provider
        self.max_tokens = max_tokens
        self.strategy = strategy

    async def _safe_count_tokens(self, text: str) -> int:
        """
        Safely count tokens with fallback estimation.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Token count (estimated if actual counting fails)
        """
        if not text:
            return 0
        try:
            return await self.provider.count_tokens(text)
        except Exception as e:
            logger.warning(f"Token counting failed, using estimate: {e}")
            # Fallback: rough estimate of ~4 chars per token
            return len(text) // 4

    async def prepare_prompt(self, 
                             user_input: str, 
                             system_instruction: str, 
                             context_data: Optional[str] = None, 
                             history: Optional[list[dict[str, str]]] = None) -> str:
        """
        Prepare the final prompt ensuring it fits within the token limit.
        Prioritizes: System instruction > User input > Context data > History.
        
        Args:
            user_input: The user's query
            system_instruction: System prompt/instruction
            context_data: Optional database schema context
            history: Optional conversation history
            
        Returns:
            Prepared prompt string
        """
        
        try:
            # 1. Estimate base tokens with safe counting
            system_tokens = await self._safe_count_tokens(system_instruction) if system_instruction else 0
            user_tokens = await self._safe_count_tokens(user_input)
            
            # Reserve some buffer for the answer
            output_buffer = 1000 
            available_tokens = self.max_tokens - output_buffer - system_tokens - user_tokens
            
            if available_tokens < 0:
                logger.warning("User input + system instruction exceed token limit! Truncating user input.")
                # This is extreme, but we must protect the limit. 
                user_input = user_input[:int(len(user_input)/2)] 
                # Recalculate (rough)
                available_tokens = 0
                
            final_context = ""
            if context_data:
                context_tokens = await self._safe_count_tokens(context_data)
                if context_tokens <= available_tokens:
                    final_context = context_data
                    available_tokens -= context_tokens
                else:
                    # Truncate context
                    logger.info(f"Context data too large ({context_tokens} > {available_tokens}). Truncating...")
                    # Simple char-based truncation as approximation
                    chars_to_keep = max(available_tokens * 3, 500)  # Keep at least 500 chars
                    final_context = context_data[:chars_to_keep] + "\n...[truncated]..."
                    available_tokens = 0

            final_history_str = ""
            if history and available_tokens > 100:
                try:
                    # Add history if space remains
                    # Format history as text
                    history_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in history])
                    history_tokens = await self._safe_count_tokens(history_text)
                    
                    if history_tokens <= available_tokens:
                        final_history_str = "\nConversation History:\n" + history_text
                    else:
                        # Take last N chars that fit
                        chars_to_keep = max(available_tokens * 3, 200)
                        truncated_history = history_text[-chars_to_keep:]
                        # Try to cut at a newline to avoid partial lines
                        first_newline = truncated_history.find('\n')
                        if first_newline != -1:
                            truncated_history = truncated_history[first_newline+1:]
                        
                        final_history_str = "\nConversation History (truncated):\n" + truncated_history
                except Exception as e:
                    logger.warning(f"Failed to process history: {e}")
                    final_history_str = ""

            # Assemble final parts
            parts = []
            if final_context:
                parts.append(f"### CONTEXT:\n{final_context}\n")
            
            if final_history_str:
                parts.append(final_history_str)
                
            parts.append(f"\nUser Input: {user_input}")
            
            return "\n".join(parts)
            
        except Exception as e:
            # Fallback: return minimal prompt if something goes wrong
            logger.error(f"Error preparing prompt: {e}")
            return f"User Input: {user_input}"

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count based on character length.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return len(text) // 4
