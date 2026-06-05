"use client";

import { useParams } from "next/navigation";

import { ConfigEditor } from "@/components/config-editor";

export default function ConfigPage() {
  const { id } = useParams<{ id: string }>();
  return <ConfigEditor key={id} id={Number(id)} />;
}
