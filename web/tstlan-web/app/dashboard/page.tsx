import { GaugeIcon } from "@phosphor-icons/react/ssr";

import { PagePlaceholder } from "@/components/page-placeholder";

export default function DashboardPage() {
  return (
    <PagePlaceholder
      icon={GaugeIcon}
      title="Дашборд"
      description="Виджеты значений переменных и графики временных рядов появятся здесь."
    />
  );
}
