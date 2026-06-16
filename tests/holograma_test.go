package tests

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/chromedp/cdproto/page"
	"github.com/chromedp/chromedp"
)

// Configuración básica
const (
	baseURL = "http://localhost:8000" // Cambiar a la URL del frontend de Holograma UNEV
)

// --- Helpers Modulares y Reutilizables (Filosofía Ponytail: Sin sobreingeniería) ---

// submitPassword realiza el flujo de escribir contraseña y hacer clic en desbloquear
func submitPassword(password string) chromedp.Action {
	return chromedp.Tasks{
		chromedp.WaitVisible("#passwordPrompt", chromedp.ByID),
		chromedp.SendKeys("#passwordInput", password, chromedp.ByID),
		chromedp.Click("#unlockBtn", chromedp.ByID),
	}
}

// sendMessage envía un mensaje al input de chat y presiona el botón de enviar
func sendMessage(message string) chromedp.Action {
	return chromedp.Tasks{
		chromedp.WaitEnabled("#chatInput", chromedp.ByID),
		chromedp.SendKeys("#chatInput", message, chromedp.ByID),
		chromedp.Click("#sendBtn", chromedp.ByID),
	}
}

// --- Casos de Prueba ---

// TestUnlockSuccess valida el flujo exitoso de desbloqueo: contraseña correcta, status dot verde, habilitación del input.
func TestUnlockSuccess(t *testing.T) {
	// Crear contexto
	ctx, cancel := chromedp.NewContext(context.Background())
	defer cancel()

	// Timeout de seguridad global del test (YAGNI de esperas infinitas)
	ctx, cancelTimeout := context.WithTimeout(ctx, 15*time.Second)
	defer cancelTimeout()

	err := chromedp.Run(ctx,
		chromedp.Navigate(baseURL),
		// Ejecutar secuencia de desbloqueo con contraseña correcta
		submitPassword("unev_admin_2026"), // Reemplazar con la clave correcta configurada
		// Esperar que el dot de estado cambie a verde (el selector valida el estado activo)
		chromedp.WaitVisible("#statusDot.green", chromedp.ByQuery),
		// Verificar que el input de chat ya no esté deshabilitado
		chromedp.WaitEnabled("#chatInput", chromedp.ByID),
	)

	if err != nil {
		t.Fatalf("Error en el flujo de desbloqueo exitoso: %v", err)
	}
	t.Log("Flujo de desbloqueo exitoso validado correctamente.")
}

// TestWrongPasswordAlert valida el flujo de fallo: contraseña incorrecta y control de alertas JS.
func TestWrongPasswordAlert(t *testing.T) {
	ctx, cancel := chromedp.NewContext(context.Background())
	defer cancel()

	ctx, cancelTimeout := context.WithTimeout(ctx, 10*time.Second)
	defer cancelTimeout()

	alertTextChan := make(chan string, 1)

	// Ponytail-style native listener: captura eventos de diálogos/alertas del navegador nativamente
	chromedp.ListenTarget(ctx, func(ev interface{}) {
		if ev, ok := ev.(*page.EventJavascriptDialogOpening); ok {
			alertTextChan <- ev.Message
			// Aceptar automáticamente la alerta para evitar colgar la automatización
			go func() {
				_ = chromedp.Run(ctx, page.HandleJavaScriptDialog(true))
			}()
		}
	})

	err := chromedp.Run(ctx,
		chromedp.Navigate(baseURL),
		submitPassword("contraseña_incorrecta_prueba"),
	)
	if err != nil {
		t.Fatalf("Error al ejecutar interacción de contraseña incorrecta: %v", err)
	}

	// Validar que se recibió la alerta dentro de un tiempo prudente
	select {
	case msg := <-alertTextChan:
		t.Logf("Alerta interceptada correctamente: '%s'", msg)
		if !strings.Contains(strings.ToLower(msg), "incorrecta") && !strings.Contains(strings.ToLower(msg), "error") {
			t.Errorf("Mensaje de alerta inesperado: '%s'", msg)
		}
	case <-time.After(3 * time.Second):
		t.Error("No se detectó ninguna alerta de diálogo JS tras introducir una contraseña inválida.")
	}
}

// TestChatStreamingComplete valida que la IA recibe un prompt y detecta cuándo termina de hacer streaming
// basándose en eventos nativos del DOM (desaparición de indicadores de carga o reactivación de inputs).
func TestChatStreamingComplete(t *testing.T) {
	ctx, cancel := chromedp.NewContext(context.Background())
	defer cancel()

	// Timeout de seguridad más amplio debido a la generación de texto del LLM
	ctx, cancelTimeout := context.WithTimeout(ctx, 40*time.Second)
	defer cancelTimeout()

	var finalResponse string

	err := chromedp.Run(ctx,
		chromedp.Navigate(baseURL),
		submitPassword("unev_admin_2026"),
		chromedp.WaitVisible("#statusDot.green", chromedp.ByQuery),
		
		// Enviar el prompt
		sendMessage("¿Cuál es la misión de la Universidad Virtual UNEV?"),
		
		// Monitoreo de streaming: Esperamos que la animación de carga se oculte (display: none)
		// y que el input del chat vuelva a habilitarse.
		chromedp.WaitNotVisible("#typingIndicator", chromedp.ByID),
		chromedp.WaitEnabled("#chatInput", chromedp.ByID),
		
		// Obtener el texto completo generado en el último globo de diálogo del bot
		chromedp.Text(".message.bot:last-child", &finalResponse, chromedp.ByQuery),
	)

	if err != nil {
		t.Fatalf("Error en el flujo de streaming del chat: %v", err)
	}

	if len(strings.TrimSpace(finalResponse)) == 0 {
		t.Error("La respuesta recibida del bot está vacía.")
	} else {
		t.Logf("Streaming finalizado correctamente. Respuesta de IA: '%s...'", finalResponse[:60])
	}
}
