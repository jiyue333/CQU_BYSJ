/**
 * 文件上传 API 封装
 * Requirements: 1.1
 */

import type { FileUploadResponse, FileListResponse, FileInfo } from '@/types'
import { handleResponse, ApiRequestError } from './request'

const API_BASE = '/api/files'

// ApiRequestError and handleResponse moved to ./request

/**
 * 上传视频文件
 */
export async function uploadFile(
  file: File,
  onProgress?: (progress: number) => void
): Promise<FileUploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const formData = new FormData()
    formData.append('file', file)

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress((e.loaded / e.total) * 100)
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText))
        } catch {
          reject(new ApiRequestError(xhr.status, 'Invalid JSON response'))
        }
      } else {
        let detail = `HTTP ${xhr.status}`
        try {
          const error = JSON.parse(xhr.responseText)
          detail = error.detail || detail
        } catch {
          // ignore
        }
        reject(new ApiRequestError(xhr.status, detail))
      }
    })

    xhr.addEventListener('error', () => {
      reject(new ApiRequestError(0, 'Network error'))
    })

    xhr.addEventListener('abort', () => {
      reject(new ApiRequestError(0, 'Upload aborted'))
    })

    xhr.open('POST', `${API_BASE}/upload`)
    xhr.send(formData)
  })
}

/**
 * 获取文件列表
 */
export async function listFiles(): Promise<FileListResponse> {
  const response = await fetch(API_BASE)
  return handleResponse<FileListResponse>(response)
}

/**
 * 获取文件信息
 */
export async function getFile(fileId: string): Promise<FileInfo> {
  const response = await fetch(`${API_BASE}/${fileId}`)
  return handleResponse<FileInfo>(response)
}

/**
 * 删除文件
 */
export async function deleteFile(fileId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/${fileId}`, {
    method: 'DELETE'
  })
  return handleResponse<void>(response)
}


