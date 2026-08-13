"use client";

import React, { useState } from "react";
import ChatSidebar from "@/components/public/ChatSidebar";
import ChatWindow from "@/components/public/ChatWindow";
import { usePersona } from "@/context/PersonaContext";

export default function ChatPage() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const { persona, setPersona } = usePersona();

  const handlePersonaChange = (newPersona: "public" | "student" | "staff") => {
    setPersona(newPersona);
    setConversationId(null);
  };

  return (
    <div className="flex h-screen bg-white dark:bg-slate-950 overflow-hidden">
      <ChatSidebar
        activeConversationId={conversationId}
        onNewChat={() => setConversationId(null)}
        onSelectConversation={setConversationId}
        persona={persona}
        onPersonaChange={handlePersonaChange}
      />
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <ChatWindow conversationId={conversationId} onConversationIdChange={setConversationId} />
      </main>
    </div>
  );
}
