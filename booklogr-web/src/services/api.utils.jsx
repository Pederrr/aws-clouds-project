export const getAPIUrl = (endpoint) => {
	const baseUrl = new URL(import.meta.env.VITE_API_ENDPOINT, window.location.origin);
	const normalizedEndpoint = String(endpoint ?? '').replace(/^\//, '');
	return new URL(normalizedEndpoint, baseUrl).toString();
};
