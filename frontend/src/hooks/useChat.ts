import { useMutation } from "@tanstack/react-query";

import { sendChatMessage } from "../services/api";

export function useChat() {
  return useMutation({
    mutationFn: ({
      message,
      sessionId,
      context,
    }: {
      message: string;
      sessionId?: string;
      context?: { title?: string; hint?: string };
    }) => sendChatMessage(message, sessionId, context),
  });
}
