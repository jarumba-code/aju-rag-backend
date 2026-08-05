import React from "react";

interface SuggestedPillsProps {
  questions: string[];
  onSelectQuestion: (question: string) => void;
}

export const SuggestedPills: React.FC<SuggestedPillsProps> = ({
  questions,
  onSelectQuestion,
}) => {
  if (!questions || questions.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 w-full mt-2">
      <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider select-none">
        Suggested Questions
      </span>
      <div className="flex flex-wrap gap-2">
        {questions.map((question, index) => (
          <button
            key={index}
            onClick={() => onSelectQuestion(question)}
            className="text-left text-xs px-3 py-2 rounded-xl bg-white/10 dark:bg-slate-800/40 border border-slate-200/50 dark:border-slate-700/50 text-slate-700 dark:text-slate-300 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 hover:border-blue-400 dark:hover:from-blue-950/20 dark:hover:to-indigo-950/20 dark:hover:border-blue-500 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 shadow-sm hover:shadow-md cursor-pointer outline-none focus:ring-2 focus:ring-blue-500/20"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedPills;
