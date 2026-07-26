import React, { useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import axios from "axios";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

export default function App() {
  const [file, setFile] = useState(null);
  const [age, setAge] = useState(18);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [zipUrl, setZipUrl] = useState("");
  const [error, setError] = useState("");

  const onDrop = (acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setError("");
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"]
    },
    maxFiles: 1
  });

  const preview = useMemo(() => (file ? URL.createObjectURL(file) : ""), [file]);

  const generate = async () => {
    if (!file) {
      setError("Please upload an image first.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const form = new FormData();
      form.append("image", file);
      form.append("current_age", age.toString());

      const response = await axios.post(`${API_BASE}/generate`, form, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      setResults(response.data.images || []);
      setZipUrl(`${API_BASE}${response.data.zip_url}`);
    } catch (err) {
      const message = err?.response?.data?.detail || "Generation failed. Please try a different portrait.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-white text-slate-800">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <h1 className="text-center text-4xl font-bold tracking-tight">Face Aging AI</h1>
        <p className="mx-auto mt-3 max-w-2xl text-center text-slate-600">
          Upload a portrait, enter current age, and generate realistic age progression every 3 years up to age 60.
        </p>

        <section className="mt-10 grid gap-8 rounded-2xl border border-slate-200 p-6 md:grid-cols-2">
          <div>
            <h2 className="text-lg font-semibold">1. Upload Portrait</h2>
            <div
              {...getRootProps()}
              className={`mt-3 cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition ${
                isDragActive ? "border-blue-500 bg-blue-50" : "border-slate-300"
              }`}
            >
              <input {...getInputProps()} />
              {file ? (
                <p className="text-sm font-medium text-slate-700">Selected: {file.name}</p>
              ) : (
                <p className="text-sm text-slate-500">Drag & drop a JPG/PNG here, or click to browse</p>
              )}
            </div>

            {preview && <img src={preview} alt="Preview" className="mt-4 h-64 w-full rounded-xl object-cover" />}
          </div>

          <div>
            <h2 className="text-lg font-semibold">2. Set Current Age</h2>
            <input
              type="number"
              min={0}
              max={60}
              value={age}
              onChange={(e) => setAge(Number(e.target.value))}
              className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-lg"
            />

            <button
              onClick={generate}
              disabled={loading}
              className="mt-6 w-full rounded-lg bg-slate-900 px-4 py-3 font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
            >
              {loading ? "Generating..." : "Generate Age Progression"}
            </button>

            {zipUrl && (
              <a
                href={zipUrl}
                className="mt-4 inline-block rounded-lg bg-blue-600 px-4 py-2 font-medium text-white"
                download
              >
                Download All as ZIP
              </a>
            )}

            {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
          </div>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-semibold">3. Generated Images</h2>
          {results.length === 0 ? (
            <p className="mt-2 text-slate-500">No generated images yet.</p>
          ) : (
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {results.map((item) => {
                const imageUrl = `${API_BASE}${item.url}`;
                return (
                  <div key={item.age} className="rounded-xl border border-slate-200 p-3 shadow-sm">
                    <img src={imageUrl} alt={`Age ${item.age}`} className="h-56 w-full rounded-lg object-cover" />
                    <div className="mt-2 flex items-center justify-between">
                      <span className="font-medium">Age {item.age}</span>
                      <a
                        href={`${API_BASE}/download/${item.url.split("/")[2]}/${item.filename}`}
                        className="text-sm text-blue-600 hover:underline"
                        download
                      >
                        Download
                      </a>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
