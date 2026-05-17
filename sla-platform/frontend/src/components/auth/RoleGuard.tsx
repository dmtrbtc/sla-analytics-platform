import { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { Result } from "antd";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "../../stores/authStore";

interface RoleGuardProps {
  roles: string[];
  children: ReactNode;
}

export default function RoleGuard({ roles, children }: RoleGuardProps) {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!roles.includes(user.role)) {
    return (
      <Result
        status="403"
        title="403"
        subTitle={t("roleGuard.forbidden")}
      />
    );
  }

  return <>{children}</>;
}
