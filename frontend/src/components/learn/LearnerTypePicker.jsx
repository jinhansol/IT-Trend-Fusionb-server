// Optional learner type choice. "선택 안 함" (null) is always available.
import { LEARNER_TYPES } from "../../learner/learnerTypes";

export default function LearnerTypePicker({ value, onChange, name = "learner_type" }) {
  const options = [...LEARNER_TYPES, { value: null, label: "선택 안 함", description: "나중에 설정에서 고를 수 있어요" }];
  return (
    <fieldset>
      <legend className="block text-sm font-medium text-gray-700 mb-2">학습자 유형 (선택)</legend>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {options.map((option) => {
          const checked = value === option.value;
          return (
            <label
              key={option.value ?? "none"}
              className={`flex gap-2 items-start border rounded-lg p-3 cursor-pointer text-left ${
                checked ? "border-indigo-500 bg-indigo-50" : "border-gray-200"
              }`}
            >
              <input
                type="radio"
                name={name}
                className="mt-1"
                checked={checked}
                onChange={() => onChange(option.value)}
              />
              <span>
                <span className="block text-sm font-semibold">{option.label}</span>
                <span className="block text-xs text-gray-500">{option.description}</span>
              </span>
            </label>
          );
        })}
      </div>
      <p className="text-xs text-gray-500 mt-2">시작 안내에만 쓰이며, 보이는 콘텐츠나 순서는 바뀌지 않아요.</p>
    </fieldset>
  );
}
