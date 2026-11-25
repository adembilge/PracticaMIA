import type { ChatMessage } from "../lib/api";

type MessageListProps = {
  messages: ChatMessage[];
};

export function MessageList({ messages }: MessageListProps) {
  return (
    <div>
    {messages.map((message) => (
      <article key={message.id} className={message.role}>
        <p>{message.content}</p>
        {message.citations.length > 0 ? (
          <div>
            {message.citations.map((citation) => (
              <p key={citation.chunk_id}>
                <a href={citation.url}>{citation.title}</a>
                {citation.heading ? ` — ${citation.heading}` : null}
              </p>
            ))}
          </div>
        ) : null}
      </article>
    ))}
    </div>
  );
}