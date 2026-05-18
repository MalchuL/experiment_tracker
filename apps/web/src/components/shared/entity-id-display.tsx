type EntityIdDisplayProps = {
  label: string;
  value: string;
};

export function EntityIdDisplay({ label, value }: EntityIdDisplayProps) {
  return (
    <div className="text-xs font-mono text-muted-foreground p-2 bg-muted/50 rounded-md">
      {label}: {value}
    </div>
  );
}
