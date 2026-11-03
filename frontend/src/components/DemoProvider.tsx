'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { messages, type Locale } from '@/lib/i18n';

export type Answer = 'yes' | 'no' | 'unsure';
type Phase = 'scope' | 'intake' | 'checklist';
export type Field = 'previousAddress' | 'newAddress' | 'movedOn';

export interface DemoCase {
  goal: string;
  answers: (Answer | null)[];
  questionIndex: number;
  phase: Phase;
  previousAddress: string;
  newAddress: string;
  movedOn: string;
  factsConfirmed: boolean;
}

const initialCase: DemoCase = {
  goal: '', answers: [null, null, null, null, null], questionIndex: 0, phase: 'scope',
  previousAddress: '', newAddress: '', movedOn: '', factsConfirmed: false,
};

interface DemoContextValue {
  locale: Locale;
  t: (typeof messages)[Locale];
  toggleLocale: () => void;
  data: DemoCase;
  setGoal: (goal: string) => void;
  answer: (index: number, value: Answer) => void;
  setQuestionIndex: (index: number) => void;
  setPhase: (phase: Phase) => void;
  updateField: (field: Field, value: string) => void;
  confirmFacts: () => void;
  reset: () => void;
}

const DemoContext = createContext<DemoContextValue | null>(null);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>('en');
  const [data, setData] = useState<DemoCase>(initialCase);
  useEffect(() => { document.documentElement.lang = locale; }, [locale]);
  const toggleLocale = useCallback(() => setLocale((old) => (old === 'en' ? 'it' : 'en')), []);
  const setGoal = useCallback((goal: string) => setData((old) => ({ ...old, goal })), []);
  const answer = useCallback((index: number, value: Answer) => {
    setData((old) => {
      const changed = old.answers[index] !== value;
      const answers = [...old.answers];
      answers[index] = value;
      if (changed) {
        for (let i = index + 1; i < answers.length; i += 1) answers[i] = null;
      }
      return { ...old, answers, questionIndex: index, phase: 'scope', factsConfirmed: changed ? false : old.factsConfirmed };
    });
  }, []);
  const setQuestionIndex = useCallback((index: number) => setData((old) => ({ ...old, questionIndex: Math.min(4, Math.max(0, index)), phase: 'scope' })), []);
  const setPhase = useCallback((phase: Phase) => setData((old) => ({ ...old, phase })), []);
  const updateField = useCallback((field: Field, value: string) => setData((old) => ({ ...old, [field]: value, phase: 'intake', factsConfirmed: false })), []);
  const confirmFacts = useCallback(() => setData((old) => ({ ...old, phase: 'checklist', factsConfirmed: true })), []);
  const reset = useCallback(() => setData({ ...initialCase, answers: [...initialCase.answers] }), []);
  const value = useMemo(() => ({ locale, t: messages[locale], toggleLocale, data, setGoal, answer, setQuestionIndex, setPhase, updateField, confirmFacts, reset }),
    [locale, toggleLocale, data, setGoal, answer, setQuestionIndex, setPhase, updateField, confirmFacts, reset]);
  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export function useDemo() {
  const value = useContext(DemoContext);
  if (!value) throw new Error('useDemo must be used within DemoProvider');
  return value;
}
