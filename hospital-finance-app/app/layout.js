import './globals.css'

export const metadata = {
  title: '온소아청소년과의원 재정관리',
  description: '병원 재정관리 시스템',
}

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  )
}
