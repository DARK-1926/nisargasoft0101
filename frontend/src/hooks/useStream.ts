import { useEffect, useRef } from "react";

import { streamUrl } from "../api";

export function useStream(onMessage: (event: MessageEvent<string>) => void) {
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    const source = new EventSource(streamUrl);
    const handler = (event: Event) => {
      onMessageRef.current(event as MessageEvent<string>);
    };
    source.addEventListener("snapshot.updated", handler);
    source.addEventListener("alert.created", handler);
    return () => {
      source.removeEventListener("snapshot.updated", handler);
      source.removeEventListener("alert.created", handler);
      source.close();
    };
  }, []);
}
