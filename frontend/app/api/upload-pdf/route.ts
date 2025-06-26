import { NextRequest, NextResponse } from "next/server"

// 백엔드 PDF 업로드 API URL
const PDF_UPLOAD_API_URL = "http://pdf-api:8013/upload-pdf"

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get("file") as File | null

    if (!file) {
      return NextResponse.json({ error: "파일이 없습니다." }, { status: 400 })
    }

    // 백엔드 API로 formData를 그대로 전달
    const backendResponse = await fetch(PDF_UPLOAD_API_URL, {
      method: "POST",
      body: formData
    })

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json()
      console.error("PDF 업로드 백엔드 오류:", errorData)
      return NextResponse.json(
        { error: "파일 업로드에 실패했습니다.", details: errorData },
        { status: backendResponse.status }
      )
    }

    const responseData = await backendResponse.json()
    return NextResponse.json(responseData)
  } catch (error) {
    console.error("PDF 업로드 프록시 오류:", error)
    return NextResponse.json(
      { error: "서버 내부 오류가 발생했습니다." },
      { status: 500 }
    )
  }
} 