import { useSearchParams } from "react-router-dom";

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/**
 * The technology filter lives in the address (?tech=python), so Career can link to a
 * filtered Home or Dev list and the filter survives a reload. Invalid values are ignored.
 */
export function useTechParam() {
  const [params, setParams] = useSearchParams();
  const raw = params.get("tech");
  const tech = raw && SLUG.test(raw) ? raw : null;
  const setTech = (value) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value) next.set("tech", value);
        else next.delete("tech");
        return next;
      },
      { replace: true }
    );
  return [tech, setTech];
}
