"use client";
import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

// Legacy /c/[cafeId]/[tableId] route — table number is now typed by the customer.
// Redirect to the parent route so old QR codes still land somewhere sensible.
export default function LegacyTableRedirect() {
  const params = useParams<{ cafeId: string }>();
  const router = useRouter();
  useEffect(() => {
    router.replace(`/c/${params.cafeId}`);
  }, [router, params.cafeId]);
  return (
    <main className="min-h-dvh grid place-items-center text-muted text-sm">
      Redirecting…
    </main>
  );
}
