export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
      <h1 className="font-heading text-2xl font-semibold tracking-tight">TSTLAN</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        Веб-платформа мониторинга и отладки приборов по протоколам MxNet, Modbus
        и USB HID.
      </p>
    </main>
  );
}
