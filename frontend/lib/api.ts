// Export the base URL as a constant for use throughout the application
// Can be overridden by environment variable for different deployments
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/";
