import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Camera, FileImage, FileText, Trash2, Upload, X } from "lucide-react";
import { API_BASE, endpoints } from "../lib/api";

const CATEGORIES = [
  { id: "delivery", label: "Delivery Proof", icon: FileImage,
    hint: "Attach proof-of-delivery photos or PDFs. Tie each upload to a task ID." },
  { id: "incident", label: "Incident Evidence", icon: FileText,
    hint: "Attach photos or logs to failure / collision events (use agent or event ID)." },
  { id: "recon", label: "Field Recon", icon: Camera,
    hint: "Environment and obstacle imagery captured in the field." },
];

export default function FilesPage({ state, integrations }) {
  const [params] = useSearchParams();
  const [category, setCategory] = useState(params.get("category") || "recon");
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(null);
  const [refId, setRefId] = useState(params.get("ref") || "");
  const [caption, setCaption] = useState("");
  const fileRef = useRef(null);

  useEffect(() => {
    const cat = params.get("category");
    const ref = params.get("ref");
    if (cat) setCategory(cat);
    if (ref) setRefId(ref);
  }, [params]);

  const cat = useMemo(() => CATEGORIES.find((c) => c.id === category), [category]);

  const load = async () => {
    try {
      const r = await endpoints.listFiles({ category });
      setItems(r.files || []);
    } catch { setError("Could not load files"); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [category]);

  const upload = async (e) => {
    e.preventDefault();
    const f = fileRef.current?.files?.[0];
    if (!f) return;
    if (f.size > 10 * 1024 * 1024) { setError("File exceeds 10 MB"); return; }
    setBusy(true); setError("");
    const fd = new FormData();
    fd.append("file", f);
    fd.append("category", category);
    if (refId) fd.append("ref_id", refId);
    if (caption) fd.append("caption", caption);
    try {
      const res = await fetch(`${API_BASE}/api/files/upload`, { method: "POST", body: fd });
      if (!res.ok) throw new Error((await res.json()).detail || "Upload failed");
      setRefId(""); setCaption("");
      if (fileRef.current) fileRef.current.value = "";
      await load();
    } catch (e) {
      setError(String(e.message || e));
    } finally { setBusy(false); }
  };

  const del = async (id) => {
    try {
      await endpoints.deleteFile(id);
      setItems((prev) => prev.filter((x) => x.id !== id));
    } catch { setError("Delete failed"); }
  };

  const enabled = integrations?.storage_enabled;

  return (
    <div data-testid="files-page">
      <div className="page-header">
        <div>
          <div className="crumbs">/ files · media evidence & recon</div>
          <h1 className="display">Field files</h1>
          <p className="muted">Delivery proof, incident evidence, and recon imagery — stored in Emergent Object Storage.</p>
        </div>
      </div>

      {!enabled && (
        <div className="panel warning-panel" data-testid="files-offline">
          Object storage is not enabled on the server. Uploads are disabled.
        </div>
      )}

      <div className="files-cats" data-testid="files-category-tabs">
        {CATEGORIES.map((c) => {
          const Icon = c.icon;
          const active = category === c.id;
          return (
            <button
              key={c.id}
              className={`file-cat ${active ? "active" : ""}`}
              onClick={() => setCategory(c.id)}
              data-testid={`files-cat-${c.id}`}
            >
              <Icon size={16} />
              <span>{c.label}</span>
            </button>
          );
        })}
      </div>

      <div className="split-3" style={{ gridTemplateColumns: "360px 1fr", gap: 20 }}>
        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">UPLOAD</span>
              <h2>{cat?.label}</h2>
            </div>
          </div>
          <p className="muted" style={{ fontSize: 13, margin: "4px 0 14px" }}>{cat?.hint}</p>
          <form onSubmit={upload} className="task-form">
            <label>
              <span>File (image or PDF, max 10 MB)</span>
              <input
                type="file"
                accept="image/*,application/pdf"
                ref={fileRef}
                required
                disabled={!enabled || busy}
                data-testid="files-file-input"
              />
            </label>
            <label>
              <span>Reference ID {category === "delivery" ? "(task DEL-###)" : category === "incident" ? "(agent DR-### or event id)" : "(optional)"}</span>
              <input
                type="text"
                value={refId}
                onChange={(e) => setRefId(e.target.value)}
                placeholder={category === "delivery" ? "DEL-001" : category === "incident" ? "DR-003" : ""}
                disabled={!enabled || busy}
                data-testid="files-ref-input"
              />
            </label>
            <label>
              <span>Caption (optional)</span>
              <input
                type="text"
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                placeholder="Short description"
                disabled={!enabled || busy}
                data-testid="files-caption-input"
              />
            </label>
            {error && <div className="form-error" data-testid="files-error">{error}</div>}
            <button
              type="submit"
              className="btn primary"
              disabled={!enabled || busy}
              data-testid="files-upload-button"
            >
              <Upload size={14} /> {busy ? "Uploading…" : "Upload"}
            </button>
          </form>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">GALLERY</span>
              <h2>{items.length} file{items.length === 1 ? "" : "s"}</h2>
            </div>
          </div>
          {items.length === 0 && <p className="muted">No files yet in this category.</p>}
          <div className="files-grid" data-testid="files-gallery">
            {items.map((f) => (
              <FileCard key={f.id} file={f} onOpen={() => setPreview(f)} onDelete={() => del(f.id)} />
            ))}
          </div>
        </div>
      </div>

      {preview && (
        <div className="overlay" onClick={() => setPreview(null)}>
          <div className="overlay-inner" onClick={(e) => e.stopPropagation()} data-testid="files-preview">
            <header>
              <div>
                <span className="panel-kicker">{preview.category.toUpperCase()}</span>
                <h3>{preview.original_filename}</h3>
                {preview.caption && <p className="muted">{preview.caption}</p>}
              </div>
              <button className="btn ghost" onClick={() => setPreview(null)} data-testid="files-preview-close"><X size={14} /></button>
            </header>
            <div className="files-preview-body">
              {preview.content_type?.startsWith("image/") ? (
                <img src={`${API_BASE}/api/files/${preview.id}/download`} alt={preview.original_filename} />
              ) : (
                <a
                  className="btn primary"
                  href={`${API_BASE}/api/files/${preview.id}/download`}
                  target="_blank"
                  rel="noreferrer"
                >Open {preview.original_filename}</a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function FileCard({ file, onOpen, onDelete }) {
  const isImg = file.content_type?.startsWith("image/");
  return (
    <div className="file-card" data-testid={`file-card-${file.id}`}>
      <button className="file-thumb" onClick={onOpen} data-testid={`file-open-${file.id}`}>
        {isImg
          ? <img src={`${API_BASE}/api/files/${file.id}/download`} alt={file.original_filename} loading="lazy" />
          : <div className="pdf-thumb"><FileText size={22} /> PDF</div>}
      </button>
      <div className="file-meta">
        <div className="file-name" title={file.original_filename}>{file.original_filename}</div>
        <div className="file-sub">
          {file.ref_id && <span className="pill muted">{file.ref_id}</span>}
          <span className="muted">{(file.size / 1024).toFixed(1)} KB</span>
        </div>
        {file.caption && <div className="file-caption">{file.caption}</div>}
        <button className="btn ghost tiny" onClick={onDelete} data-testid={`file-delete-${file.id}`}>
          <Trash2 size={12} /> Delete
        </button>
      </div>
    </div>
  );
}
