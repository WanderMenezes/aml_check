import { redirect } from "next/navigation";

export default function ScreeningsRedirectPage() {
  redirect("/screening/new");
}
