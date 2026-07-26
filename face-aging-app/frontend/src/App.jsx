import { useMemo, useState } from 'react'
import axios from 'axios'
import UploadZone from './components/UploadZone'
import ResultCard from './components/ResultCard'

export default function App() {
  const [file, setFile] = useState(null)
  const [age, setAge] = useState(10)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : ''), [file])

  const onGenerate = async () => {
    if (!file) {
      setError('Please upload an image before generating.')
      return
    }

    setError('')
    setLoading(true)
    setResult(null)

    const formData = new FormData()
    formData.append('image', file)
    formData.append('current_age', Number(age))

    try {
      const { data } = await axios.post('/api/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(data)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Generation failed. Please retry.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-white p-6 md:p-10">
      <div className="max-w-6xl mx-auto">
        <header className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900">Face Aging Simulator</h1>
          <p className="text-gray-600 mt-2">Upload one portrait and generate realistic age progression every 3 years up to 60.</p>
        </header>

        <section className="bg-white border rounded-2xl p-6 md:p-8 shadow-sm space-y-6">
          <UploadZone file={file} setFile={setFile} />

          {previewUrl && (
            <div className="max-w-xs mx-auto">
              <img src={previewUrl} alt="Preview" className="rounded-xl border object-cover w-full aspect-square" />
            </div>
          )}

          <div className="max-w-sm mx-auto">
            <label className="block text-sm font-medium text-gray-700 mb-2">Current age</label>
            <input
              type="number"
              min="0"
              max="60"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              className="w-full border rounded-xl px-4 py-3 focus:ring-2 focus:ring-gray-900 outline-none"
            />
          </div>

          <div className="text-center">
            <button
              onClick={onGenerate}
              disabled={loading}
              className="px-8 py-3 rounded-xl bg-gray-900 text-white font-medium disabled:opacity-60 hover:bg-black"
            >
              {loading ? 'Generating...' : 'Generate'}
            </button>
          </div>

          {error && <p className="text-center text-red-600">{error}</p>}
        </section>

        {result && (
          <section className="mt-10">
            <div className="flex flex-wrap gap-3 items-center justify-between mb-5">
              <h2 className="text-2xl font-semibold text-gray-900">Generated Faces</h2>
              <a href={result.zip_url} className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-black">
                Download ZIP
              </a>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {result.images.map((item) => (
                <ResultCard key={item.age} item={item} />
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  )
}
