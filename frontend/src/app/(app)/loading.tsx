import { Skeleton } from "@/components/shared/skeleton";

export default function Loading() {
  return (
    <div className="grid gap-5 lg:grid-cols-4">
      <Skeleton className="h-36" />
      <Skeleton className="h-36" />
      <Skeleton className="h-36" />
      <Skeleton className="h-36" />
      <Skeleton className="col-span-full h-96" />
    </div>
  );
}
