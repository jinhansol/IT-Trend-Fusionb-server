// Loader.jsx
export default function Loader() {
  return (
    <div className="flex justify-center items-center h-64">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500"></div>
      <p className="ml-3 text-indigo-600 font-semibold">Loading...</p>
    </div>
  );
}
