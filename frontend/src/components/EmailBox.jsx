export default function EmailBox({ subject, body, recipient }) {
  return (
    <div className="email-box">
      <div>
        <strong>Para:</strong> <span>{recipient || '...'}</span>
      </div>
      <div>
        <strong>Asunto:</strong> <span>{subject || '...'}</span>
      </div>
      <div className="email-body">
        <p>{body || 'El contenido generado del correo aparecerá aquí.'}</p>
      </div>
    </div>
  )
}
