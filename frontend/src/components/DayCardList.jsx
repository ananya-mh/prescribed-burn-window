import DayCard from "./DayCard";

// Stacks vertically on narrow screens, sits in a row on wide ones.
export default function DayCardList({ days }) {
  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-start">
      {days.map((day) => (
        <DayCard key={day.date} day={day} />
      ))}
    </div>
  );
}
