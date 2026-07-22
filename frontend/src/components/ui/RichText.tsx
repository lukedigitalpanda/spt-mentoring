// Renders a News article / Mass message body.
//
// The backend (backend/apps/news/sanitiser.py) is the sanitisation
// authority: News.body and MassMessage body are stored either as
// nh3-sanitised HTML (when the admin used the rich text editor) or as
// byte-identical plain text otherwise. This component mirrors the
// backend's exact HTML_TAG_RE / is_rich_text() test so both ends agree on
// which bodies are "rich" - if the regexes ever drift, plain text with a
// stray "<x>" could render as (already-sanitised) HTML on one end and as
// literal text on the other.
//
// SAFETY: this is a dangerouslySetInnerHTML render. It does NOT sanitise
// client-side - it trusts that `body` came from a backend field that runs
// every write through the sanitiser (News.body, MassMessage body). It must
// never be fed unsanitised, user-authored content (chat messages, forum
// posts) - those are a separate, unsanitised path and rendering them here
// would be an XSS hole.
const HTML_RE = /<([a-z]+)(\s[^>]*)?>/i;

export default function RichText({ body, className = '' }: { body: string; className?: string }) {
  if (HTML_RE.test(body)) {
    return (
      <div
        className={`rich-text break-words ${className}`}
        dangerouslySetInnerHTML={{ __html: body }}
      />
    );
  }
  return <div className={`whitespace-pre-wrap break-words ${className}`}>{body}</div>;
}
