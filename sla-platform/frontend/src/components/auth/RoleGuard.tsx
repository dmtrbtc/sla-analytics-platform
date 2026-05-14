import { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { Result } from "antd";
import { useAuthStore } from "../../stores/authStore";

interface RoleGuardProps {
  roles: string[];
  children: ReactNode;
}

export default function RoleGuard({ roles, children }: RoleGuardProps) {
  const user = useAuthStore((s) => s.user);

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!roles.includes(user.role)) {
    return (
      <Result
        status="403"
        title="403"
        subTitle="You do not have permission to access this page."
      />
    );
  }

  return <>{children}</>;
}
