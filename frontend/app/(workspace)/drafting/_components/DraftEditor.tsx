"use client";

import { Mark, mergeAttributes, type JSONContent } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import { Button } from "@/app/components/ui/Button";
import { CardLabel } from "@/app/components/ui/Card";

export type Evidence = {
  id: number;
  citation_type: string;
  title: string;
  source?: string | null;
  snippet: string;
  confidence: number;
  status: string;
};

export type EditableDraftDocument = {
  id: number;
  document_type: string;
  title: string;
  content: string;
  editor_json?: JSONContent | null;
  generated_editor_json?: JSONContent | null;
  status: string;
  error_status?: string | null;
  revision_count: number;
  edit_revision: number;
  last_edited_at?: string | null;
  last_edited_by?: number | null;
};

type DraftEditorProps = {
  document: EditableDraftDocument;
  evidence: Evidence[];
  authHeaders: Record<string, string>;
  onDocumentSaved: (document: EditableDraftDocument) => void;
  onError: (message: string) => void;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
};

const CitationRef = Mark.create({
  name: "citationRef",

  addAttributes() {
    return {
      evidenceId: {
        default: null,
        parseHTML: (element) => Number(element.getAttribute("data-citation-evidence-id")),
        renderHTML: (attributes) => ({
          "data-citation-evidence-id": attributes.evidenceId,
        }),
      },
      label: {
        default: null,
        parseHTML: (element) => element.getAttribute("data-citation-label"),
        renderHTML: (attributes) =>
          attributes.label ? { "data-citation-label": attributes.label } : {},
      },
    };
  },

  parseHTML() {
    return [{ tag: "span[data-citation-evidence-id]" }];
  },

  renderHTML({ HTMLAttributes }) {
    return ["span", mergeAttributes(HTMLAttributes, { class: "citation-ref" }), 0];
  },
});

function textToTiptapJson(text: string): JSONContent {
  const blocks = text
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);
  return {
    type: "doc",
    content: blocks.length
      ? blocks.map((block) => ({
          type: "paragraph",
          content: [{ type: "text", text: block.replace(/\n/g, " ") }],
        }))
      : [{ type: "paragraph" }],
  };
}

function saveStatusLabel({
  dirty,
  saving,
  error,
  savedAt,
}: {
  dirty: boolean;
  saving: boolean;
  error: string | null;
  savedAt: string | null;
}) {
  if (saving) return "Saving";
  if (error) return "Save failed";
  if (dirty) return "Unsaved";
  if (savedAt) return `Saved ${savedAt}`;
  return "Saved";
}

export function DraftEditor({
  document,
  evidence,
  authHeaders,
  onDocumentSaved,
  onError,
  isFullscreen,
  onToggleFullscreen,
}: DraftEditorProps) {
  const [revision, setRevision] = useState(document.edit_revision || 0);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<number | "">(
    evidence[0]?.id ?? "",
  );
  const autosaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const documentIdRef = useRef(document.id);
  const revisionRef = useRef(document.edit_revision || 0);

  const initialContent = useMemo(
    () => document.editor_json ?? textToTiptapJson(document.content),
    [document.content, document.editor_json],
  );

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
      }),
      CitationRef,
    ],
    content: initialContent,
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: "draft-editor-content",
      },
    },
    onUpdate: () => {
      setDirty(true);
      setSaveError(null);
    },
  });

  const saveDocument = useCallback(
    async (revisionType: "manual" | "autosave" = "manual") => {
      if (!editor || saving) return;
      setSaving(true);
      setSaveError(null);
      try {
        const res = await fetch(`${API_BASE_URL}drafting/documents/${documentIdRef.current}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json", ...authHeaders },
          credentials: "include",
          body: JSON.stringify({
            editor_json: editor.getJSON(),
            expected_revision: revisionRef.current,
            revision_type: revisionType,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          const detail = data.detail === "stale_revision"
            ? "This draft changed elsewhere. Reload the matter before saving."
            : data.detail || "Draft save failed.";
          throw new Error(detail);
        }
        const savedDocument = data.document as EditableDraftDocument;
        revisionRef.current = savedDocument.edit_revision || 0;
        setRevision(revisionRef.current);
        setDirty(false);
        setSavedAt(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
        onDocumentSaved(savedDocument);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Draft save failed.";
        setSaveError(message);
        onError(message);
      } finally {
        setSaving(false);
      }
    },
    [authHeaders, editor, onDocumentSaved, onError, saving],
  );

  useEffect(() => {
    if (!editor || !dirty || saving) return;
    if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
    autosaveTimerRef.current = setTimeout(() => {
      void saveDocument("autosave");
    }, 1800);
    return () => {
      if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
    };
  }, [dirty, editor, saveDocument, saving]);

  useEffect(() => {
    if (!editor) return;
    const incomingRevision = document.edit_revision || 0;
    const changedDocument = document.id !== documentIdRef.current;
    const changedCleanRevision = incomingRevision !== revisionRef.current && !dirty;
    if (!changedDocument && !changedCleanRevision) return;
    documentIdRef.current = document.id;
    revisionRef.current = incomingRevision;
    setRevision(revisionRef.current);
    setDirty(false);
    setSaveError(null);
    setSavedAt(null);
    editor.commands.setContent(document.editor_json ?? textToTiptapJson(document.content), {
      emitUpdate: false,
    });
  }, [dirty, document, editor]);

  useEffect(() => {
    if (selectedEvidenceId === "" && evidence[0]) {
      setSelectedEvidenceId(evidence[0].id);
    }
  }, [evidence, selectedEvidenceId]);

  const selectedEvidence = evidence.find((item) => item.id === selectedEvidenceId);

  const insertCitation = () => {
    if (!editor || !selectedEvidence) return;
    editor
      .chain()
      .focus()
      .insertContent({
        type: "text",
        text: selectedEvidence.title,
        marks: [
          {
            type: "citationRef",
            attrs: { evidenceId: selectedEvidence.id, label: selectedEvidence.title },
          },
        ],
      })
      .run();
  };

  const previewExport = () => {
    window.open(`${API_BASE_URL}drafting/documents/${document.id}/export/preview`, "_blank", "noopener,noreferrer");
  };

  const downloadDocx = async () => {
    const res = await fetch(`${API_BASE_URL}drafting/documents/${document.id}/export/docx`, {
      headers: authHeaders,
      credentials: "include",
    });
    if (!res.ok) {
      onError("DOCX export failed.");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const anchor = window.document.createElement("a");
    anchor.href = url;
    anchor.download = `${document.title.toLowerCase().replaceAll(" ", "-")}.docx`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="draft-editor-shell">
      <div className="draft-editor-toolbar" aria-label="Draft editor toolbar">
        <div className="draft-editor-tool-group">
          <button type="button" onClick={() => editor?.chain().focus().toggleBold().run()} className={editor?.isActive("bold") ? "active" : ""} aria-label="Bold" title="Bold">
            <i className="fas fa-bold"></i>
          </button>
          <button type="button" onClick={() => editor?.chain().focus().toggleItalic().run()} className={editor?.isActive("italic") ? "active" : ""} aria-label="Italic" title="Italic">
            <i className="fas fa-italic"></i>
          </button>
          <button type="button" onClick={() => editor?.chain().focus().toggleStrike().run()} className={editor?.isActive("strike") ? "active" : ""} aria-label="Strikethrough" title="Strikethrough">
            <i className="fas fa-strikethrough"></i>
          </button>
          <div className="draft-editor-divider"></div>
          <button type="button" onClick={() => editor?.chain().focus().toggleBulletList().run()} className={editor?.isActive("bulletList") ? "active" : ""} aria-label="Bullet list" title="Bullet List">
            <i className="fas fa-list-ul"></i>
          </button>
          <button type="button" onClick={() => editor?.chain().focus().toggleOrderedList().run()} className={editor?.isActive("orderedList") ? "active" : ""} aria-label="Numbered list" title="Numbered List">
            <i className="fas fa-list-ol"></i>
          </button>
          <button type="button" onClick={() => editor?.chain().focus().toggleBlockquote().run()} className={editor?.isActive("blockquote") ? "active" : ""} aria-label="Blockquote" title="Blockquote">
            <i className="fas fa-quote-right"></i>
          </button>
          <div className="draft-editor-divider"></div>
          <button type="button" onClick={() => editor?.chain().focus().undo().run()} disabled={!editor?.can().undo()} aria-label="Undo" title="Undo">
            <i className="fas fa-undo"></i>
          </button>
          <button type="button" onClick={() => editor?.chain().focus().redo().run()} disabled={!editor?.can().redo()} aria-label="Redo" title="Redo">
            <i className="fas fa-redo"></i>
          </button>
        </div>

        <div className="draft-editor-citation-controls">
          <select
            aria-label="Citation evidence"
            value={selectedEvidenceId}
            onChange={(event) => setSelectedEvidenceId(Number(event.target.value))}
            disabled={!evidence.length}
          >
            {evidence.length ? evidence.map((item) => (
              <option key={item.id} value={item.id}>{item.title}</option>
            )) : (
              <option value="">No citations</option>
            )}
          </select>
          <Button variant="secondary" size="sm" disabled={!selectedEvidence} onClick={insertCitation}>
            Cite
          </Button>
        </div>

        <div className="draft-editor-save-controls">
          <span className={`draft-editor-save-state ${saveError ? "error" : dirty ? "dirty" : "saved"}`}>
            <span className="save-status-dot"></span>
            {saveStatusLabel({ dirty, saving, error: saveError, savedAt })}
          </span>
          <span className="mono-text text-slate-400">r{revision}</span>
          <Button variant="secondary" size="sm" onClick={() => saveDocument("manual")} loading={saving} disabled={!editor || saving || !dirty}>
            Save
          </Button>
          <Button variant="secondary" size="sm" onClick={previewExport}>
            Preview
          </Button>
          <Button variant="secondary" size="sm" onClick={downloadDocx}>
            DOCX
          </Button>
          {onToggleFullscreen && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onToggleFullscreen}
              title={isFullscreen ? "Exit Full Screen" : "Full Screen"}
              className="fullscreen-toggle-btn"
            >
              <i className={`fas ${isFullscreen ? "fa-compress" : "fa-expand"}`}></i>
            </Button>
          )}
        </div>
      </div>

      <div className="paper-meta">
        <strong>REPUBLIC OF KENYA</strong>
        <span>Editable pleading draft</span>
        <span className="mono-text">{document.document_type.replaceAll("_", " ")}</span>
      </div>
      <div className="document-divider-title">{document.title}</div>
      <CardLabel className="mb-3">Draft body</CardLabel>
      <EditorContent editor={editor} />
    </div>
  );
}
