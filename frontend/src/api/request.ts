import type { ApiError } from '@/types'

export class ApiRequestError extends Error {
    status: number
    detail: string

    constructor(status: number, detail: string) {
        super(detail)
        this.name = 'ApiRequestError'
        this.status = status
        this.detail = detail
    }
}

export async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        let detail = `HTTP ${response.status}`
        try {
            const error: ApiError = await response.json()
            detail = error.detail || detail
        } catch {
            // ignore JSON parse error
        }
        throw new ApiRequestError(response.status, detail)
    }

    // Handle 204 No Content
    if (response.status === 204) {
        return undefined as T
    }

    return response.json()
}
