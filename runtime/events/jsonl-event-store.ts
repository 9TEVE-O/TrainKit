/**
 * Append-only JSONL event store.
 *
 * Every event written to the store is a single JSON object on its own line.
 * The store never modifies or deletes existing lines; it only appends.
 *
 * Default storage path: .runtime/events/events.jsonl (relative to cwd).
 */

import { appendFileSync, mkdirSync, readFileSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { randomUUID } from "node:crypto";
import type { EventEnvelope, EventType } from "../runtime-types.js";

export const DEFAULT_EVENT_LOG_PATH = ".runtime/events/events.jsonl";

export interface JsonlEventStore {
  /** Append a new event to the log. Returns the persisted envelope. */
  append<T>(type: EventType, payload: T): EventEnvelope<T>;
  /** Read all events from the log (most recently-written last). */
  readAll(): EventEnvelope<unknown>[];
  /** Absolute path of the underlying JSONL file. */
  readonly path: string;
}

/**
 * Create a JSONL event store backed by a file at `logPath`.
 *
 * The directory is created automatically if it does not exist.
 */
export function createJsonlEventStore(
  logPath: string = DEFAULT_EVENT_LOG_PATH
): JsonlEventStore {
  const absolutePath = resolve(logPath);

  function ensureDir(): void {
    mkdirSync(dirname(absolutePath), { recursive: true });
  }

  function append<T>(type: EventType, payload: T): EventEnvelope<T> {
    const envelope: EventEnvelope<T> = {
      id: randomUUID(),
      timestamp: new Date().toISOString(),
      type,
      payload,
    };
    ensureDir();
    appendFileSync(absolutePath, JSON.stringify(envelope) + "\n", "utf8");
    return envelope;
  }

  function readAll(): EventEnvelope<unknown>[] {
    if (!existsSync(absolutePath)) return [];
    const lines = readFileSync(absolutePath, "utf8")
      .split("\n")
      .filter((l) => l.trim().length > 0);
    return lines.map((line) => JSON.parse(line) as EventEnvelope<unknown>);
  }

  return {
    append,
    readAll,
    get path() {
      return absolutePath;
    },
  };
}
