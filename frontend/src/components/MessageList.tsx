import type { ChatMessage } from "../lib/api";
import { CitationList } from "./CitationList";

type MessageListProps = {
  messages: ChatMessage[];
};

export function MessageList({ messages }: MessageListProps) {
  return (
    <div>
      {messages.map((message) => (
        <article key={message.id} className={message.role}>
          <p>{message.content}</p>
          <CitationList citations={message.citations} />
        </article>
      ))}
    </div>
  );
}
