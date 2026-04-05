import * as React from "react";
import { cn } from "@/lib/utils";

const variants = {
  default: "bg-primary text-primary-foreground",
  muted: "bg-muted text-foreground",
  success: "bg-emerald-100 text-emerald-900",
  danger: "bg-rose-100 text-rose-900",
  warning: "bg-amber-100 text-amber-900"
};

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  variant?: keyof typeof variants;
}) {
  return (
    <div
      className={cn(
        "inline-flex w-fit items-center rounded-full px-3 py-1 text-xs font-medium uppercase tracking-[0.2em]",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

