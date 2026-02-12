#!/usr/bin/env python3
"""
Session Management for xBridge MCP

Provides persistent conversation history and session management capabilities.
Sessions are stored in JSON files for persistence across server restarts.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any
from pathlib import Path


class SessionManager:
    """Manages conversation sessions with persistent storage."""

    def __init__(self, storage_dir: str = ".grok_sessions"):
        """
        Initialize session manager.

        Args:
            storage_dir: Directory to store session files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self._load_sessions()

    def _load_sessions(self):
        """Load existing sessions from disk."""
        for session_file in self.storage_dir.glob("*.json"):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    session_id = session_data.get("session_id")
                    if session_id:
                        self.active_sessions[session_id] = session_data
            except Exception as e:
                print(f"Error loading session {session_file}: {e}")

    def _save_session(self, session_id: str):
        """Save session to disk."""
        if session_id not in self.active_sessions:
            return

        session_file = self.storage_dir / f"{session_id}.json"
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(self.active_sessions[session_id], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving session {session_id}: {e}")

    def create_session(self,
                      name: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session.

        Args:
            name: Optional human-readable name for the session
            metadata: Optional metadata to attach to the session

        Returns:
            Session ID (UUID)
        """
        session_id = str(uuid.uuid4())

        self.active_sessions[session_id] = {
            "session_id": session_id,
            "name": name or f"Session {session_id[:8]}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "conversation_history": [],
            "tool_chain_history": [],
        }

        self._save_session(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by ID."""
        return self.active_sessions.get(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions with basic info."""
        return [
            {
                "session_id": sid,
                "name": session.get("name"),
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "message_count": len(session.get("conversation_history", [])),
            }
            for sid, session in self.active_sessions.items()
        ]

    def add_message(self,
                   session_id: str,
                   role: str,
                   content: str,
                   metadata: Optional[Dict[str, Any]] = None):
        """
        Add a message to session conversation history.

        Args:
            session_id: Session ID
            role: Message role (user/assistant)
            content: Message content
            metadata: Optional metadata (model used, tokens, etc.)
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        session["conversation_history"].append(message)
        session["updated_at"] = datetime.now().isoformat()
        self._save_session(session_id)

    def get_conversation_history(self,
                                session_id: str,
                                limit: Optional[int] = None,
                                format_for_api: bool = True) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session.

        Args:
            session_id: Session ID
            limit: Optional limit on number of messages (most recent)
            format_for_api: If True, return in API format (role + content only)

        Returns:
            List of messages
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        history = session.get("conversation_history", [])

        if limit:
            history = history[-limit:]

        if format_for_api:
            # Return only role and content for API calls
            return [
                {"role": msg["role"], "content": msg["content"]}
                for msg in history
            ]

        return history

    def add_tool_chain_step(self,
                           session_id: str,
                           step_name: str,
                           tool_name: str,
                           arguments: Dict[str, Any],
                           result: Any,
                           metadata: Optional[Dict[str, Any]] = None):
        """
        Record a tool chain execution step.

        Args:
            session_id: Session ID
            step_name: Name of the chaining step
            tool_name: Tool that was executed
            arguments: Arguments passed to the tool
            result: Result from the tool
            metadata: Optional additional metadata
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        step = {
            "step_name": step_name,
            "tool_name": tool_name,
            "arguments": arguments,
            "result": str(result)[:1000],  # Truncate for storage
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        session["tool_chain_history"].append(step)
        session["updated_at"] = datetime.now().isoformat()
        self._save_session(session_id)

    def delete_session(self, session_id: str):
        """Delete a session and its storage file."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

            session_file = self.storage_dir / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()

    def clear_conversation(self, session_id: str):
        """Clear conversation history but keep the session."""
        session = self.get_session(session_id)
        if session:
            session["conversation_history"] = []
            session["tool_chain_history"] = []
            session["updated_at"] = datetime.now().isoformat()
            self._save_session(session_id)


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
