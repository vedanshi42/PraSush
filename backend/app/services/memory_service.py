from typing import List, Dict, Any

class MemoryManager:
    def __init__(self, max_history_turns: int = 5):
        self.max_history_turns = max_history_turns
        # Maps session_id to list of chat exchanges
        # Each entry: {"role": "user"|"assistant", "content": str}
        self.sessions: Dict[str, List[Dict[str, str]]] = {}

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def add_user_message(self, session_id: str, message: str):
        history = self.get_history(session_id)
        history.append({"role": "user", "content": message})
        self._truncate(session_id)

    def add_assistant_message(self, session_id: str, message: str):
        history = self.get_history(session_id)
        history.append({"role": "assistant", "content": message})
        self._truncate(session_id)

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def get_formatted_context(self, session_id: str) -> str:
        history = self.get_history(session_id)
        if not history:
            return "No previous conversation history."
        
        context_lines = []
        for turn in history:
            role_label = "User" if turn["role"] == "user" else "PraSush"
            context_lines.append(f"{role_label}: {turn['content']}")
        return "\n".join(context_lines)

    def _truncate(self, session_id: str):
        history = self.sessions[session_id]
        # 1 turn = 1 user + 1 assistant message, so count * 2 messages
        limit = self.max_history_turns * 2
        if len(history) > limit:
            self.sessions[session_id] = history[-limit:]

# Global single instance for session tracking
memory_manager = MemoryManager()
