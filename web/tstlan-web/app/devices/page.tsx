import { HardDrivesIcon } from "@phosphor-icons/react/ssr";

import { PagePlaceholder } from "@/components/page-placeholder";

export default function DevicesPage() {
  return (
    <PagePlaceholder
      icon={HardDrivesIcon}
      title="Устройства"
      description="Список приборов, транспорты (MxNet, Modbus, USB HID) и схемы переменных."
    />
  );
}
