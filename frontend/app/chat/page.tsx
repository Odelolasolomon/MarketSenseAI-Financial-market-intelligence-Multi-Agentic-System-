"use client";

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { Loader } from "@/components/ai-elements/loader";
import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputMessage,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from "@/components/ai-elements/prompt-input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";

import { useChat } from "@ai-sdk/react";
import { CopyIcon, RefreshCcwIcon } from "lucide-react";
import { Fragment, useState } from "react";

const suggestions = [
  "Should I invest in buying Bitcoin now?",
  "what stocks are likely to perform well this quarter?",
  "BTC vs ETH - which is a better investment?",
];

const ASSETS = [
  "BTC",
  "ETH",
  "BNB",
  "ADA",
  "SOL",
  "XRP",
  "DOT",
  "DOGE",
  "AVAX",
  "MATIC",
] as const;

const TIMEFRAMES = ["short", "medium", "long"] as const;

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [selectedAsset, setSelectedAsset] = useState<string>("BTC");
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>("medium");

  const { messages, sendMessage, status, regenerate } = useChat();

  const handleSubmit = (message: PromptInputMessage) => {
  const hasText = Boolean(message.text.trim());

  if (!hasText) {
    return;
  }

  sendMessage(
    { text: message.text.trim() },
    {
      body: {
        asset: selectedAsset,
        timeframe: selectedTimeframe,
      },
    }
  );
  setInput("");
};

  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(
      { text: suggestion },
      {
        body: {
          asset: selectedAsset,
          timeframe: selectedTimeframe,
        },
      }
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-6 relative size-full h-screen font-mono">
      <div className="flex flex-col h-full">
        <Conversation className="h-full">
          <ConversationContent>
            {messages.length === 0 ? (
              <ConversationEmptyState
                title="Hello there! 👋"
                description="I'm MarketSenseAI. How can I help you today?"
              />
            ) : (
              messages.map((message, messageIndex) => (
                <Fragment key={message.id}>
                  {message.parts.map((part, partIndex) => {
                    switch (part.type) {
                      case "text":
                        const isLastMessage =
                          messages.length - 1 === messageIndex;

                        return (
                          <Fragment key={`${message.id}-${partIndex}`}>
                            <Message from={message.role}>
                              <MessageContent>
                                <MessageResponse>{part.text}</MessageResponse>
                              </MessageContent>
                            </Message>
                            {message.role === "assistant" && isLastMessage && (
                              <MessageActions>
                                <MessageAction
                                  onClick={() => regenerate()}
                                  label="Retry"
                                >
                                  <RefreshCcwIcon className="size-3" />
                                </MessageAction>
                                <MessageAction
                                  onClick={() =>
                                    navigator.clipboard.writeText(part.text)
                                  }
                                  label="Copy"
                                >
                                  <CopyIcon className="size-3" />
                                </MessageAction>
                              </MessageActions>
                            )}
                          </Fragment>
                        );
                      default:
                        return null;
                    }
                  })}
                </Fragment>
              ))
            )}

            {status === "submitted" && <Loader />}
          </ConversationContent>
          <ConversationScrollButton />
        </Conversation>

        <div className="grid shrink-0 gap-4 pt-4">
          <Suggestions className="px-4">
            {suggestions.map((suggestion) => (
              <Suggestion
                key={suggestion}
                onClick={() => handleSuggestionClick(suggestion)}
                suggestion={suggestion}
              />
            ))}
          </Suggestions>
        </div>

        <PromptInput
          onSubmit={handleSubmit}
          className="mt-4 w-full max-w-2xl mx-auto relative"
          globalDrop
          multiple
        >
          <PromptInputBody>
            <PromptInputTextarea
              value={input}
              onChange={(e) => setInput(e.currentTarget.value)}
              placeholder="Type your message..."
              className="pr-12"
            />
          </PromptInputBody>
          <PromptInputFooter>
            <PromptInputTools className="flex items-center gap-2">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="font-medium">Asset:</span>
                <Select
                  value={selectedAsset}
                  onValueChange={setSelectedAsset}
                  required
                >
                  <SelectTrigger className="h-8 w-[120px] text-xs">
                    <SelectValue placeholder="Select asset" />
                  </SelectTrigger>
                  <SelectContent>
                    {ASSETS.map((asset) => (
                      <SelectItem key={asset} value={asset} className="text-xs">
                        {asset}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="font-medium">Timeframe:</span>
                <Select
                  value={selectedTimeframe}
                  onValueChange={setSelectedTimeframe}
                  required
                >
                  <SelectTrigger className="h-8 w-[100px] text-xs capitalize">
                    <SelectValue placeholder="Select timeframe" />
                  </SelectTrigger>
                  <SelectContent>
                    {TIMEFRAMES.map((timeframe) => (
                      <SelectItem
                        key={timeframe}
                        value={timeframe}
                        className="text-xs capitalize"
                      >
                        {timeframe}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </PromptInputTools>
          </PromptInputFooter>
          <PromptInputSubmit
            status={status === "streaming" ? "streaming" : "ready"}
            disabled={!input.trim() && !status}
            className="absolute bottom-1 right-1 bg-blue-500"
          />
        </PromptInput>
      </div>
    </div>
  );
}