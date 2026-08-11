"use client";

import React, { useState } from "react";
import { ChevronDown } from "lucide-react";

interface FAQItem {
  question: string;
  answer: string;
}

interface FAQAccordionProps {
  items: FAQItem[];
}

export default function FAQAccordion({ items }: FAQAccordionProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div
          key={index}
          className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden"
        >
          <button
            onClick={() => setOpenIndex(openIndex === index ? null : index)}
            className="w-full flex items-center justify-between px-5 py-4 text-left"
            aria-expanded={openIndex === index}
            aria-controls={`faq-answer-${index}`}
          >
            <span className="text-sm font-medium text-slate-800 dark:text-slate-200 pr-4">
              {item.question}
            </span>
            <ChevronDown
              size={18}
              className={`flex-shrink-0 text-slate-400 transition-transform duration-200 ${openIndex === index ? "rotate-180" : ""}`}
            />
          </button>
          {openIndex === index && (
            <div
              id={`faq-answer-${index}`}
              className="px-5 pb-4 text-sm text-slate-600 dark:text-slate-300 leading-relaxed animate-fade-in"
            >
              {item.answer}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
