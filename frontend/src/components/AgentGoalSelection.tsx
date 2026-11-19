export type GoalSelection = {
  language: 'en' | 'it';
  options: string[];
  active_goal: number | null;
};

export function AgentGoalSelection({selection}: {selection: GoalSelection}) {
  const en = selection.language === 'en';
  const heading = en ? 'Task choices' : 'Pratiche disponibili';
  return (
    <section aria-label={heading} lang={selection.language}>
      <h2>{heading}</h2>
      <ul>
        {selection.options.map((option, index) => {
          const active = index + 1 === selection.active_goal;
          return (
            <li key={option} aria-current={active || undefined}>
              {active ? <strong>{option} · {en ? 'Active task' : 'Pratica attiva'}</strong> : option}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
