// Static start guidance on the Career home. Same text for everyone with the same
// learner type; guests and members without a type get the common guide (policy C-2).
import { Link } from "react-router-dom";
import { startGuideFor } from "../../learner/learnerTypes";

const LINK =
  "text-sm font-semibold px-3 py-1.5 rounded-lg bg-white border border-indigo-200 text-indigo-700 hover:bg-indigo-100";

export default function StartGuide({ learnerType }) {
  const guide = startGuideFor(learnerType);
  return (
    <section aria-label="시작 안내" className="rounded-2xl border border-indigo-100 bg-indigo-50/60 p-5 mb-8">
      <h2 className="font-bold mb-1">{guide.title}</h2>
      <p className="text-sm text-slate-600 mb-3">{guide.body}</p>
      <div className="flex flex-wrap gap-2">
        {guide.links.map((link) =>
          link.href ? (
            <a key={link.href} href={link.href} className={LINK}>
              {link.label}
            </a>
          ) : (
            <Link key={link.to} to={link.to} className={LINK}>
              {link.label}
            </Link>
          )
        )}
      </div>
    </section>
  );
}
