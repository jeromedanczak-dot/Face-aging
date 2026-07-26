export default function ResultCard({ item }) {
  return (
    <div className="bg-white border rounded-xl p-3 shadow-sm">
      <img src={item.url} alt={`Age ${item.age}`} className="rounded-lg w-full aspect-square object-cover" />
      <div className="mt-3 flex items-center justify-between">
        <span className="font-semibold text-gray-800">Age {item.age}</span>
        <a
          href={item.url}
          download={item.filename}
          className="text-sm px-3 py-1.5 rounded-lg bg-gray-900 text-white hover:bg-black"
        >
          Download
        </a>
      </div>
    </div>
  )
}
