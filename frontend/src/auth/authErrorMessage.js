// Korean messages for DevHub 2.0 auth error codes (see backend app/services/auth.py).
export function authErrorMessage(error) {
  switch (error?.code) {
    case "INVALID_CREDENTIALS":
      return "이메일 또는 비밀번호가 올바르지 않습니다.";
    case "TOO_MANY_ATTEMPTS": {
      const seconds = error.details?.retry_after;
      return seconds
        ? `로그인 시도가 너무 많습니다. ${seconds}초 후 다시 시도해 주세요.`
        : "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.";
    }
    case "EMAIL_ALREADY_REGISTERED":
      return "이미 가입된 이메일입니다.";
    case "VALIDATION_ERROR":
      return "입력값을 확인해 주세요. 비밀번호는 8~128자, 이름은 1~50자입니다.";
    case "NETWORK_ERROR":
    case "TIMEOUT":
      return "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.";
    default:
      return "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";
  }
}
