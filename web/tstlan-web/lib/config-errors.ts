import { ApiError } from "@/lib/api";

export function describeSaveError(cause: unknown): string {
  if (cause instanceof ApiError) {
    if (cause.status === 403) return "недостаточно прав";
    if (cause.status === 404) return "конфиг не найден";
    if (cause.status === 422) return "проверьте поля формы";
  }
  return "не удалось сохранить";
}

export function describeShareError(cause: unknown): string {
  if (cause instanceof ApiError) {
    if (cause.status === 404) return "пользователь не найден";
    if (cause.status === 422) return "нельзя выдать доступ владельцу";
    if (cause.status === 403) return "недостаточно прав";
  }
  return "не удалось изменить доступ";
}
