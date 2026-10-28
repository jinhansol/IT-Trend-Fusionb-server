// Renders learning content written in Markdown (tables via GFM).
// Raw HTML in the source is dropped (skipHtml), so content files cannot inject markup.
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const components = {
  h2: (props) => <h3 className="text-lg font-bold mt-5 mb-2" {...props} />,
  h3: (props) => <h4 className="font-bold mt-4 mb-2" {...props} />,
  p: (props) => <p className="leading-relaxed my-2" {...props} />,
  ul: (props) => <ul className="list-disc pl-5 my-2 space-y-1" {...props} />,
  ol: (props) => <ol className="list-decimal pl-5 my-2 space-y-1" {...props} />,
  a: (props) => (
    <a className="text-indigo-600 underline" target="_blank" rel="noopener noreferrer" {...props} />
  ),
  pre: (props) => (
    <pre className="bg-slate-900 text-slate-100 text-sm rounded-lg p-4 my-3 overflow-x-auto" {...props} />
  ),
  code: ({ className, ...props }) =>
    className ? (
      <code className={className} {...props} />
    ) : (
      <code className="bg-slate-100 text-slate-800 px-1 py-0.5 rounded text-[0.9em]" {...props} />
    ),
  table: (props) => (
    <div className="overflow-x-auto my-3">
      <table className="min-w-full text-sm border border-slate-200" {...props} />
    </div>
  ),
  th: (props) => <th className="border border-slate-200 bg-slate-50 px-3 py-2 text-left" {...props} />,
  td: (props) => <td className="border border-slate-200 px-3 py-2" {...props} />,
};

export default function Markdown({ children }) {
  return (
    <div className="text-slate-700">
      <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
