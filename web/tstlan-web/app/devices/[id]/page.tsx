"use client";

import { useParams } from "next/navigation";

import { DeviceMonitor } from "@/components/device-monitor";

export default function DevicePage() {
  const { id } = useParams<{ id: string }>();
  return <DeviceMonitor deviceId={id} />;
}
