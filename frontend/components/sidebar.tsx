"use client";

import { useEffect, useState } from "react";
import { PlusIcon, MessageSquareIcon } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface ConversationSummary {
    conversation_id: string;
    asset_symbol: string;
    message_count: number;
    last_updated: string;
}

interface SidebarProps {
    userId: string;
    currentConversationId?: string;
    onSelectConversation: (id: string) => void;
    onNewChat: () => void;
    refreshKey?: number;
}

export function Sidebar({
    userId,
    currentConversationId,
    onSelectConversation,
    onNewChat,
    refreshKey,
}: SidebarProps) {
    const [conversations, setConversations] = useState<ConversationSummary[]>([]);

    useEffect(() => {
        if (!userId) return;

        fetch(`${process.env.NEXT_PUBLIC_API_URL}/conversations/user/${userId}`)
            .then(res => res.ok ? res.json() : [])
            .then(setConversations)
            .catch(() => { });
    }, [userId, refreshKey]);

    return (
        <div className="w-64 h-screen bg-[#f9f9f9] border-r border-[#e5e5e5] flex flex-col">
            {/* New Chat Button */}
            <div className="p-2">
                <button
                    onClick={onNewChat}
                    className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg hover:bg-white transition-colors text-sm font-medium"
                >
                    <PlusIcon className="w-4 h-4" />
                    New chat
                </button>
            </div>

            {/* Conversations */}
            <div className="flex-1 overflow-y-auto px-2">
                <div className="text-xs font-semibold text-gray-500 px-3 py-2">Your chats</div>
                {conversations.map((conv) => (
                    <button
                        key={conv.conversation_id}
                        onClick={() => onSelectConversation(conv.conversation_id)}
                        className={`w-full flex items-start gap-2 px-3 py-2 rounded-lg hover:bg-white transition-colors text-left text-sm mb-1 ${currentConversationId === conv.conversation_id ? 'bg-white' : ''
                            }`}
                    >
                        <MessageSquareIcon className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                            <div className="truncate font-medium">{conv.asset_symbol} Analysis</div>
                            <div className="text-xs text-gray-500 truncate">
                                {formatDistanceToNow(new Date(conv.last_updated), { addSuffix: true })}
                            </div>
                        </div>
                    </button>
                ))}
            </div>
        </div>
    );
}
