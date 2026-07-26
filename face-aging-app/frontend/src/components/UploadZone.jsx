import { useRef } from 'react'

export default function UploadZone({ file, setFile }) {
  const inputRef = useRef(null)

  const onDrop = (event) => {
    event.preventDefault()
    const dropped = event.dataTransfer.files?.[0]
    if (dropped) setFile(dropped)
  }

  const onSelect = (event) => {
    const selected = event.target.files?.[0]
    if (selected) setFile(selected)
  }

  return (
    <div
      className="border-2 border-dashed rounded-xl p-8 text-center bg-gray-50 cursor-pointer hover:border-gray-500 transition"
      onDrop={onDrop}
      onDragOver={(event) => event.preventDefault()}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".jpg,.jpeg,.png"
        className="hidden"
        onChange={onSelect}
      />
      <p className="text-gray-700 font-medium">Drag & drop a portrait photo, or click to browse</p>
      <p className="text-sm text-gray-500 mt-2">Supported formats: JPG, PNG</p>
      {file && <p className="text-sm text-green-600 mt-3">Selected: {file.name}</p>}
    </div>
  )
}
