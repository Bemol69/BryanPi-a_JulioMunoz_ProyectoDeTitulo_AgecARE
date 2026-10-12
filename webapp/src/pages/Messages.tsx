import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ChatApi } from "../api/endpoints";
import { ApiError } from "../api/client";
import { Avatar, ErrorBanner, Spinner } from "../components/ui";
import type { ChatDetail, ChatSummary } from "../api/types";

const POLL_LIST_MS = 15000;
const POLL_CHAT_MS = 5000;

function timeLabel(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  return sameDay
    ? d.toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString("es-CL", { day: "2-digit", month: "short" });
}

function daysLeft(expiresIso: string): number {
  return Math.max(0, Math.ceil((new Date(expiresIso).getTime() - Date.now()) / 86400000));
}

export default function Messages() {
  const { id } = useParams<{ id: string }>();
  const [list, setList] = useState<ChatSummary[] | null>(null);
  const [listError, setListError] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    try {
      setList((await ChatApi.list()).items);
      setListError(null);
    } catch (e) {
      setListError(e instanceof ApiError ? e.message : "No se pudieron cargar tus conversaciones.");
    }
  }, []);

  useEffect(() => {
    loadList();
    const t = setInterval(loadList, POLL_LIST_MS);
    return () => clearInterval(t);
  }, [loadList]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Mensajes</h1>
          <p>Conversa con las cuidadoras y familias directamente en AgeCare.</p>
        </div>
      </div>

      <div className="retention-note">
        🕒 Por tu privacidad, los mensajes se eliminan automáticamente <b>7 días</b> después de enviarse.
      </div>

      <div className={`chat-layout${id ? " has-thread" : ""}`}>
        <aside className="chat-list">
          {listError && <ErrorBanner message={listError} />}
          {!list && !listError && <Spinner />}
          {list && list.length === 0 && (
            <div className="chat-empty-list">
              Todavía no tienes conversaciones.
              <br />Escribe a una cuidadora desde su perfil con el botón <b>Contactar</b>.
            </div>
          )}
          {list?.map((c) => (
            <Link key={c.conversation_id} to={`/mensajes/${c.conversation_id}`}
                  className={`chat-item${c.conversation_id === id ? " active" : ""}`}>
              <div className="cg-avatar mini"><Avatar name={c.other_name} photoUrl={c.other_photo_url} /></div>
              <div className="chat-item-body">
                <div className="chat-item-top">
                  <b>{c.other_name}</b>
                  <span>{timeLabel(c.last_message_at)}</span>
                </div>
                <div className="chat-item-last">
                  {c.last_message ? `${c.last_message.mine ? "Tú: " : ""}${c.last_message.body}` : "Sin mensajes"}
                </div>
              </div>
            </Link>
          ))}
        </aside>

        <section className="chat-thread">
          {id ? <Thread key={id} id={id} onSent={loadList} /> : (
            <div className="chat-placeholder">
              <div style={{ fontSize: 42 }}>💬</div>
              <div>Elige una conversación para ver los mensajes.</div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function Thread({ id, onSent }: { id: string; onSent: () => void }) {
  const navigate = useNavigate();
  const [chat, setChat] = useState<ChatDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const lastCount = useRef(0);

  const load = useCallback(async () => {
    try {
      setChat(await ChatApi.detail(id));
      setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        navigate("/mensajes", { replace: true }); // la conversación expiró
        return;
      }
      setError(e instanceof ApiError ? e.message : "No se pudo cargar la conversación.");
    }
  }, [id, navigate]);

  useEffect(() => {
    load();
    const t = setInterval(load, POLL_CHAT_MS);
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    if (chat && chat.messages.length !== lastCount.current) {
      lastCount.current = chat.messages.length;
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [chat]);

  async function send(e: FormEvent) {
    e.preventDefault();
    const body = draft.trim();
    if (!body || busy) return;
    setBusy(true);
    try {
      await ChatApi.send(id, body);
      setDraft("");
      await load();
      onSent();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo enviar el mensaje.");
    } finally {
      setBusy(false);
    }
  }

  if (!chat) return error ? <ErrorBanner message={error} /> : <Spinner />;

  return (
    <>
      <header className="thread-head">
        <Link to="/mensajes" className="thread-back" aria-label="Volver">←</Link>
        <div className="cg-avatar mini"><Avatar name={chat.other_name} photoUrl={chat.other_photo_url} /></div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <b>{chat.other_name}</b>
          {chat.other_profile_id && (
            <div><Link to={`/marketplace/cuidadoras/${chat.other_profile_id}`} className="care-link" style={{ fontSize: 12 }}>Ver perfil</Link></div>
          )}
        </div>
      </header>

      <div className="thread-body">
        {chat.messages.length === 0 && <div className="chat-empty-list">Aún no hay mensajes.</div>}
        {chat.messages.map((m) => (
          <div key={m.message_id} className={`bubble-row${m.mine ? " mine" : ""}`}>
            <div className="bubble">
              <div>{m.body}</div>
              <div className="bubble-meta">
                {timeLabel(m.created_at)} · se elimina en {daysLeft(m.expires_at)} {daysLeft(m.expires_at) === 1 ? "día" : "días"}
              </div>
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {error && <div style={{ padding: "0 16px" }}><ErrorBanner message={error} /></div>}
      <form className="thread-input" onSubmit={send}>
        <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Escribe un mensaje…"
               maxLength={1000} autoFocus />
        <button className="btn primary" type="submit" disabled={busy || !draft.trim()}>Enviar</button>
      </form>
    </>
  );
}
