import WorkspaceShell from "./_components/WorkspaceShell";

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <WorkspaceShell>{children}</WorkspaceShell>;
}
